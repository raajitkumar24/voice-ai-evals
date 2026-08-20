from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from voice_evals_api.config import get_settings
from voice_evals_api.db import SessionLocal
from voice_evals_api.models import (
    Agent,
    AgentConfigurationVersion,
    Conversation,
    EvalResultRecord,
    EvalRunRecord,
    FindingRecord,
    KnowledgeSourceVersion,
    ProviderConnection,
    RecommendationRecord,
    RecommendationVersionRecord,
    RetrievalEventRecord,
    ToolCallRecord,
    ToolDefinitionVersion,
)
from voice_evals_api.services.provider_runtime import provider_for_record
from voice_evals_eval_core import (
    EvalDefinition,
    EvaluationContext,
    generate_recommendation,
    load_eval_definitions,
    specialist_evaluators,
    synthesize_root_cause,
)
from voice_evals_llm_gateway import LLMGateway, ProviderRegistry
from voice_evals_schemas import (
    AgentConfigurationVersion as AgentConfigurationSchema,
)
from voice_evals_schemas import ConversationTrace, RetrievalEvent, ToolCall, Turn

from .app import celery_app


def _context_for_conversation(db: Session, conversation: Conversation) -> EvaluationContext:
    agent = db.get(Agent, conversation.agent_id)
    configuration = db.get(AgentConfigurationVersion, conversation.agent_config_version_id)
    if not agent or not configuration:
        raise RuntimeError("Conversation references a missing agent configuration")
    retrieval_records = db.scalars(
        select(RetrievalEventRecord).where(
            RetrievalEventRecord.workspace_id == conversation.workspace_id,
            RetrievalEventRecord.conversation_id == conversation.id,
        )
    ).all()
    tool_records = db.scalars(
        select(ToolCallRecord).where(
            ToolCallRecord.workspace_id == conversation.workspace_id,
            ToolCallRecord.conversation_id == conversation.id,
        )
    ).all()
    trace = ConversationTrace(
        schema_version="1.0",
        conversation_id=conversation.external_id,
        agent_id=agent.external_id,
        agent_config_version_id=configuration.external_id,
        started_at=conversation.started_at,
        ended_at=conversation.ended_at,
        channel=conversation.channel,
        metadata=conversation.trace_metadata,
        language_summary=conversation.language_summary,
        outcome=conversation.outcome,
        turns=[
            Turn(
                turn_id=turn.external_id,
                sequence=turn.sequence,
                timestamp_ms=turn.timestamp_ms,
                speaker=turn.speaker,
                text_original=turn.text_original,
                language=turn.language,
                translation=turn.translation,
            )
            for turn in conversation.turns
        ],
        retrieval_events=[
            RetrievalEvent(
                retrieval_event_id=item.external_id,
                timestamp_ms=item.timestamp_ms,
                trigger_turn_id=item.trigger_turn_id,
                query_original=item.query_original,
                query_rewritten=item.query_rewritten,
                retriever=item.retriever,
                chunks=item.chunks,
            )
            for item in retrieval_records
        ],
        tool_calls=[
            ToolCall(
                tool_call_id=item.external_id,
                tool_definition_version_id=item.tool_definition_version_id,
                trigger_turn_id=item.trigger_turn_id,
                timestamp_ms=item.timestamp_ms,
                arguments=item.arguments,
                argument_provenance=item.argument_provenance,
                status=item.status,
                result=item.result,
                duration_ms=item.duration_ms,
            )
            for item in tool_records
        ],
    )
    agent_configuration = AgentConfigurationSchema(
        id=configuration.external_id,
        agent_id=agent.external_id,
        version=configuration.version,
        prompt=configuration.prompt,
        model=configuration.model_config_data,
        tool_definition_version_ids=configuration.tool_definition_version_ids,
        knowledge_source_version_ids=configuration.knowledge_source_version_ids,
        retrieval_config=configuration.retrieval_config,
        created_at=configuration.created_at,
    )
    knowledge = db.scalars(
        select(KnowledgeSourceVersion).where(
            KnowledgeSourceVersion.workspace_id == conversation.workspace_id,
            KnowledgeSourceVersion.external_id.in_(configuration.knowledge_source_version_ids),
        )
    ).all()
    tools = db.scalars(
        select(ToolDefinitionVersion).where(
            ToolDefinitionVersion.workspace_id == conversation.workspace_id,
            ToolDefinitionVersion.external_id.in_(configuration.tool_definition_version_ids),
        )
    ).all()
    return EvaluationContext(
        trace=trace,
        agent_configuration=agent_configuration,
        knowledge_sources=[
            {
                "id": source.external_id,
                "version": source.version,
                "title": source.title,
                "content": source.parsed_text,
                "metadata": source.source_metadata,
            }
            for source in knowledge
        ],
        tool_definitions=[
            {
                "id": tool.external_id,
                "version": tool.version,
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "policy": tool.policy,
            }
            for tool in tools
        ],
    )


async def _execute(run_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        run = db.get(EvalRunRecord, run_id)
        if not run or run.status in {"CANCELLED", "COMPLETED", "PARTIALLY_COMPLETED"}:
            return
        run.status = "RUNNING"
        run.started_at = datetime.now(UTC)
        db.commit()
        snapshot = run.snapshot
        connection = db.scalar(
            select(ProviderConnection).where(
                ProviderConnection.id == snapshot["provider_connection_id"],
                ProviderConnection.workspace_id == run.workspace_id,
            )
        )
        if not connection:
            run.status = "FAILED"
            run.errors = [{"code": "PROVIDER_CONNECTION_MISSING"}]
            run.completed_at = datetime.now(UTC)
            db.commit()
            return
        provider = provider_for_record(connection, settings)
        registry = ProviderRegistry()
        registry.register(provider)
        gateway = LLMGateway(registry)
        definitions = [
            EvalDefinition.model_validate(item) for item in snapshot.get("eval_definitions", [])
        ] or load_eval_definitions()
        selected = set(snapshot.get("eval_definition_versions", []))
        definitions = [
            definition
            for definition in definitions
            if not selected or f"{definition.id}:{definition.version}" in selected
        ]
        evaluators = specialist_evaluators(definitions)
        errors: list[dict[str, Any]] = []
        contexts: dict[str, EvaluationContext] = {}
        for conversation_id in snapshot["conversation_ids"]:
            db.refresh(run)
            if run.status == "CANCELLED":
                run.completed_at = datetime.now(UTC)
                db.commit()
                return
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.workspace_id == run.workspace_id,
                    Conversation.deleted_at.is_(None),
                )
            )
            if not conversation:
                errors.append({"conversation_id": conversation_id, "code": "CONVERSATION_MISSING"})
                continue
            context = _context_for_conversation(db, conversation)
            contexts[conversation.id] = context
            for evaluator in evaluators:
                existing_result = db.scalar(
                    select(EvalResultRecord).where(
                        EvalResultRecord.run_id == run.id,
                        EvalResultRecord.conversation_id == conversation.id,
                        EvalResultRecord.evaluator_id == evaluator.definition.id,
                        EvalResultRecord.evaluator_version == evaluator.definition.version,
                    )
                )
                if existing_result:
                    continue
                try:
                    result = await evaluator.evaluate(
                        context,
                        gateway,
                        connection.provider,
                        snapshot["model"],
                        snapshot.get("routing_profile_version", "inline-v1"),
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "conversation_id": conversation.external_id,
                            "evaluator_id": evaluator.definition.id,
                            "code": type(exc).__name__,
                            "message": str(exc),
                        }
                    )
                    continue
                db.add(
                    EvalResultRecord(
                        id=result.id,
                        workspace_id=run.workspace_id,
                        run_id=run.id,
                        conversation_id=conversation.id,
                        turn_id=result.turn_id,
                        evaluator_id=result.evaluator_id,
                        evaluator_version=result.evaluator_version,
                        rubric_version=result.rubric_version,
                        verdict=result.verdict.value,
                        confidence=result.confidence,
                        severity=result.severity.value,
                        failure_code=result.failure_code,
                        reason=result.reason,
                        evidence=[item.model_dump(mode="json") for item in result.evidence],
                        judge_provenance=result.judge_provenance.model_dump(mode="json"),
                        usage=result.usage.model_dump(mode="json"),
                    )
                )
            db.commit()
        failed_results = db.scalars(
            select(EvalResultRecord).where(
                EvalResultRecord.run_id == run.id,
                EvalResultRecord.workspace_id == run.workspace_id,
                EvalResultRecord.verdict == "FAIL",
                EvalResultRecord.failure_code.is_not(None),
            )
        ).all()
        clusters: dict[str, list[EvalResultRecord]] = {}
        for failed_result in failed_results:
            key = f"{failed_result.evaluator_id}|{failed_result.failure_code}"
            clusters.setdefault(key, []).append(failed_result)
        for cluster_key, cluster_results in clusters.items():
            failure_code = cluster_results[0].failure_code
            if not failure_code:
                continue
            existing_finding = db.scalar(
                select(FindingRecord).where(
                    FindingRecord.workspace_id == run.workspace_id,
                    FindingRecord.signature == f"{run.id}|{cluster_key}",
                )
            )
            if existing_finding:
                continue
            try:
                result_payloads = [
                    {
                        "result_id": item.id,
                        "evaluator_id": item.evaluator_id,
                        "evaluator_version": item.evaluator_version,
                        "reason": item.reason,
                        "evidence": item.evidence,
                        "confidence": item.confidence,
                    }
                    for item in cluster_results
                ]
                root_cause = await synthesize_root_cause(
                    gateway,
                    connection.provider,
                    snapshot["model"],
                    failure_code,
                    result_payloads,
                )
                conversation_ids = sorted({item.conversation_id for item in cluster_results})
                language_distribution: dict[str, int] = {}
                for conversation_id in conversation_ids:
                    context = contexts[conversation_id]
                    languages = context.trace.language_summary.languages or [
                        turn.language.code for turn in context.trace.turns if turn.language
                    ]
                    for language in set(languages):
                        language_distribution[language] = language_distribution.get(language, 0) + 1
                finding = FindingRecord(
                    workspace_id=run.workspace_id,
                    source_run_id=run.id,
                    signature=f"{run.id}|{cluster_key}",
                    title=f"{failure_code.replace('_', ' ').title()} finding",
                    summary=(
                        f"{len(conversation_ids)} conversation(s) failed "
                        f"{cluster_results[0].evaluator_id}."
                    ),
                    severity=max(
                        (item.severity for item in cluster_results),
                        key=lambda value: {
                            "INFO": 0,
                            "LOW": 1,
                            "MEDIUM": 2,
                            "HIGH": 3,
                            "CRITICAL": 4,
                        }.get(value, 0),
                    ),
                    root_cause_owner=root_cause.root_cause_owner,
                    confidence=root_cause.confidence,
                    failure_codes=[failure_code],
                    result_ids=[item.id for item in cluster_results],
                    affected_conversation_ids=conversation_ids,
                    language_distribution=language_distribution,
                    representative_evidence=[
                        evidence for item in cluster_results for evidence in item.evidence
                    ][:10],
                    synthesis_provenance={
                        "evaluator_id": "root_cause",
                        "evaluator_version": "1",
                        "provider": connection.provider,
                        "model": snapshot["model"],
                    },
                )
                db.add(finding)
                db.flush()
                current_prompt = contexts[conversation_ids[0]].agent_configuration.prompt
                recommendation_output = await generate_recommendation(
                    gateway,
                    connection.provider,
                    snapshot["model"],
                    failure_code,
                    root_cause,
                    finding.representative_evidence,
                    current_prompt,
                )
                recommendation = RecommendationRecord(
                    workspace_id=run.workspace_id,
                    finding_id=finding.id,
                    status="PENDING_REVIEW",
                    change_type=recommendation_output.change_type,
                    summary=recommendation_output.summary,
                    target=recommendation_output.target,
                    current_content=recommendation_output.current_content,
                    proposed_content=recommendation_output.proposed_content,
                    rationale=recommendation_output.rationale,
                    confidence=recommendation_output.confidence,
                    requires_business_fact_verification=(
                        recommendation_output.requires_business_fact_verification
                    ),
                    synthesis_provenance={
                        "evaluator_id": "recommendation",
                        "evaluator_version": "1",
                        "provider": connection.provider,
                        "model": snapshot["model"],
                    },
                )
                db.add(recommendation)
                db.flush()
                db.add(
                    RecommendationVersionRecord(
                        workspace_id=run.workspace_id,
                        recommendation_id=recommendation.id,
                        version=1,
                        change_type=recommendation.change_type,
                        summary=recommendation.summary,
                        target=recommendation.target,
                        current_content=recommendation.current_content,
                        proposed_content=recommendation.proposed_content,
                        rationale=recommendation.rationale,
                        confidence=recommendation.confidence,
                    )
                )
                db.commit()
            except Exception as exc:
                db.rollback()
                errors.append(
                    {
                        "cluster": cluster_key,
                        "code": type(exc).__name__,
                        "message": str(exc),
                    }
                )
        persisted_results = db.scalars(
            select(EvalResultRecord).where(EvalResultRecord.run_id == run.id)
        ).all()
        result_count = len(persisted_results)
        run.counts = {
            "results": len(persisted_results),
            "pass": sum(item.verdict == "PASS" for item in persisted_results),
            "fail": sum(item.verdict == "FAIL" for item in persisted_results),
            "not_applicable": sum(item.verdict == "NOT_APPLICABLE" for item in persisted_results),
            "errors": len(errors),
        }
        run.usage = {
            key: sum(int(item.usage.get(key, 0)) for item in persisted_results)
            for key in ("input_tokens", "output_tokens", "latency_ms")
        }
        run.errors = errors
        run.status = (
            "PARTIALLY_COMPLETED"
            if errors and result_count
            else "FAILED"
            if errors
            else "COMPLETED"
        )
        run.completed_at = datetime.now(UTC)
        db.commit()


@celery_app.task(name="voice_evals.execute_eval_run")  # type: ignore[untyped-decorator]
def execute_eval_run(run_id: str) -> None:
    asyncio.run(_execute(run_id))
