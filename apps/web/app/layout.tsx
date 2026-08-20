import type {Metadata} from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Voice AI Evals",
  description: "Evidence-backed evaluation and observability for Voice AI agents",
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
