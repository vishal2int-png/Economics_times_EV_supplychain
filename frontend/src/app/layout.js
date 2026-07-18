import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "../components/layout/Sidebar";
import TopBar from "../components/layout/TopBar";
import AICopilot from "../components/ai/AICopilot";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "VoltEdge AI",
  description: "Powering India's Industrial EV Transition",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          <Sidebar />
          <div style={{ flex: 1, marginLeft: 'var(--sidebar-width)', display: 'flex', flexDirection: 'column' }}>
            <TopBar />
            <main style={{ padding: '32px', flex: 1 }}>
              {children}
            </main>
          </div>
        </div>
        <AICopilot />
      </body>
    </html>
  );
}
