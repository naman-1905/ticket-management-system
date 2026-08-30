import "./globals.css";
import { AuthProvider } from "../lib/auth-context";
import Navbar from "./components/Navbar";

export const metadata = {
  title: "Ticket Management System",
  description: "Manage support tickets, SLAs, and comments",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 min-h-screen text-slate-900 antialiased">
        <AuthProvider>
          <Navbar />
          <main>{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
