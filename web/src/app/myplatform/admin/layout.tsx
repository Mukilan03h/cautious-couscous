import Link from "next/link";
import { ReactNode } from "react";

const navItems = [
    { href: "/myplatform/admin/analytics", label: "Analytics" },
    { href: "/myplatform/admin/groups", label: "User Groups" },
    { href: "/myplatform/admin/query-history", label: "Query History" },
    { href: "/myplatform/admin/token-limits", label: "Token Limits" },
    { href: "/myplatform/admin/standard-answers", label: "Standard Answers" },
    { href: "/myplatform/admin/tenants", label: "Tenants" },
    { href: "/myplatform/admin/feature-flags", label: "Feature Flags" },
    { href: "/myplatform/admin/evals", label: "Evaluations" },
    { href: "/myplatform/admin/billing", label: "Billing" },
    { href: "/myplatform/admin/performance", label: "Performance" },
    { href: "/myplatform/admin/whitelabeling", label: "Whitelabeling" },
    { href: "/myplatform/admin/usage-export", label: "Usage Export" },
    { href: "/myplatform/admin/oauth-settings", label: "OAuth Settings" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
    return (
        <div className="flex min-h-screen">
            <aside className="w-56 bg-gray-50 border-r p-4">
                <div className="mb-6">
                    <h2 className="text-lg font-bold">Enterprise Admin</h2>
                    <p className="text-sm text-gray-500">Custom Platform</p>
                </div>
                <nav className="space-y-1">
                    {navItems.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className="block px-3 py-2 rounded hover:bg-gray-200 transition-colors"
                        >
                            {item.label}
                        </Link>
                    ))}
                </nav>
                <hr className="my-4" />
                <Link
                    href="/admin"
                    className="block px-3 py-2 rounded text-gray-600 hover:bg-gray-200"
                >
                    ← Back to ESA Admin
                </Link>
            </aside>
            <main className="flex-1 p-6 bg-white">{children}</main>
        </div>
    );
}
