import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RepoTriage",
  description: "AI-powered GitHub issue triage dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
