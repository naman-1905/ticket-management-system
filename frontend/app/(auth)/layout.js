import AuthProvider from '@/components/AuthProvider'; export default function AuthLayout({children}){return <AuthProvider><div className="auth-shell">{children}</div></AuthProvider>}
