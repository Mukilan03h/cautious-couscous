"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgOrganization from "@/icons/organization";

interface Tenant {
    id: number;
    name: string;
    slug: string;
    display_name: string | null;
    is_active: boolean;
    max_users: number | null;
    created_at: string;
}

export default function TenantsPage() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [name, setName] = useState("");
    const [slug, setSlug] = useState("");
    const [maxUsers, setMaxUsers] = useState("");

    const { data: tenants } = useSWR<Tenant[]>(
        "/api/admin/tenants/?include_inactive=true",
        errorHandlingFetcher
    );

    const handleNameChange = (value: string) => {
        setName(value);
        setSlug(value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, ""));
    };

    const handleCreate = async () => {
        const res = await fetch("/api/admin/tenants/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                slug,
                max_users: maxUsers ? parseInt(maxUsers) : undefined,
            }),
        });
        if (res.ok) {
            setIsModalOpen(false);
            setName("");
            setSlug("");
            mutate("/api/admin/tenants/?include_inactive=true");
        }
    };

    const handleToggle = async (id: number, isActive: boolean) => {
        await fetch(`/api/admin/tenants/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_active: !isActive }),
        });
        mutate("/api/admin/tenants/?include_inactive=true");
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Multi-Tenancy" icon={SvgOrganization} />

            <Text className="mb-4">
                Manage tenants (organizations) for multi-tenant deployments.
            </Text>

            <button
                onClick={() => setIsModalOpen(true)}
                className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
                Create Tenant
            </button>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg w-96">
                        <h2 className="text-xl font-bold mb-4">Create Tenant</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Name</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => handleNameChange(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="e.g., Acme Corporation"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Slug</label>
                                <input
                                    type="text"
                                    value={slug}
                                    onChange={(e) => setSlug(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Max Users</label>
                                <input
                                    type="number"
                                    value={maxUsers}
                                    onChange={(e) => setMaxUsers(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="Optional"
                                />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleCreate}
                                    disabled={!name || !slug}
                                    className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
                                >
                                    Create
                                </button>
                                <button
                                    onClick={() => setIsModalOpen(false)}
                                    className="px-4 py-2 border rounded"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <table className="w-full border-collapse border">
                <thead>
                    <tr className="bg-gray-100">
                        <th className="border p-2 text-left">Name</th>
                        <th className="border p-2 text-left">Slug</th>
                        <th className="border p-2 text-left">Max Users</th>
                        <th className="border p-2 text-left">Created</th>
                        <th className="border p-2 text-left">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {tenants?.map((tenant) => (
                        <tr key={tenant.id}>
                            <td className="border p-2 font-medium">
                                {tenant.display_name || tenant.name}
                            </td>
                            <td className="border p-2 font-mono text-sm">{tenant.slug}</td>
                            <td className="border p-2">{tenant.max_users || "Unlimited"}</td>
                            <td className="border p-2">
                                {new Date(tenant.created_at).toLocaleDateString()}
                            </td>
                            <td className="border p-2">
                                <button
                                    onClick={() => handleToggle(tenant.id, tenant.is_active)}
                                    className={`px-2 py-1 rounded text-xs ${tenant.is_active
                                            ? "bg-green-100 text-green-800"
                                            : "bg-gray-100"
                                        }`}
                                >
                                    {tenant.is_active ? "Active" : "Inactive"}
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
