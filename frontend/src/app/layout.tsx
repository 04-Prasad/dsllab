import "./globals.css";
import React from "react";
import ClientWrapper from "./ClientWrapper";

export const metadata = {
  title: "GraphGuard — Graph Fraud Detection System",
  description: "Intelligent Transaction Monitoring & Graph-based Fraud Analytics Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#05060f] text-[#d1e4fa] min-h-screen flex flex-col relative">
        <ClientWrapper>{children}</ClientWrapper>
      </body>
    </html>
  );
}
