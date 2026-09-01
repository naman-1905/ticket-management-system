import { DM_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "../lib/auth-context";
import { ThemeProvider } from "../lib/theme-context";
import Navbar from "./components/Navbar";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata = {
  title: "Ticket Management System",
  description: "Manage support tickets, SLAs, and comments",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${dmSans.variable} min-h-screen bg-background text-foreground antialiased font-sans`}>
        <ThemeProvider>
          <AuthProvider>
            <Navbar />
            <main>{children}</main>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
