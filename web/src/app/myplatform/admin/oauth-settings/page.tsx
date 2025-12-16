"use client";

import { useEffect, useState } from "react";
import { AdminPageTitle } from "@/components/admin/Title";
import { MdSecurity, MdAdd, MdDelete, MdEdit, MdCheck, MdClose, MdRefresh, MdWarning } from "react-icons/md";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface OAuthConfig {
    id: string;
    provider: string;
    client_id: string;
    enabled: boolean;
    redirect_uri: string;
    created_at: string;
}

interface OAuthConfigInput {
    provider: string;
    client_id: string;
    client_secret: string;
    redirect_uri: string;
    enabled: boolean;
}

async function fetchOAuthConfigs(): Promise<OAuthConfig[]> {
    try {
        const response = await fetch("/api/myplatform/admin/oauth-configs", {
            credentials: "include",
        });
        if (!response.ok) throw new Error("Failed to fetch configs");
        return await response.json();
    } catch (error) {
        console.error("Error fetching OAuth configs:", error);
        return [];
    }
}

async function saveOAuthConfig(config: OAuthConfigInput, id?: string): Promise<boolean> {
    try {
        const url = id
            ? `/api/myplatform/admin/oauth-configs/${id}`
            : "/api/myplatform/admin/oauth-configs";

        const response = await fetch(url, {
            method: id ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(config),
        });
        return response.ok;
    } catch (error) {
        console.error("Error saving OAuth config:", error);
        return false;
    }
}

async function deleteOAuthConfig(id: string): Promise<boolean> {
    try {
        const response = await fetch(`/api/myplatform/admin/oauth-configs/${id}`, {
            method: "DELETE",
            credentials: "include",
        });
        return response.ok;
    } catch (error) {
        console.error("Error deleting OAuth config:", error);
        return false;
    }
}

async function toggleOAuthConfig(id: string, enabled: boolean): Promise<boolean> {
    try {
        const response = await fetch(`/api/myplatform/admin/oauth-configs/${id}/toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ enabled }),
        });
        return response.ok;
    } catch (error) {
        console.error("Error toggling OAuth config:", error);
        return false;
    }
}

function OAuthConfigCard({
    config,
    onToggle,
    onEdit,
    onDelete,
}: {
    config: OAuthConfig;
    onToggle: () => void;
    onEdit: () => void;
    onDelete: () => void;
}) {
    return (
        <Card className={`shadow-sm ${!config.enabled ? "opacity-60" : ""}`}>
            <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                    <div className="flex-1">
                        <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-lg">{config.provider}</h3>
                            <span
                                className={`px-2 py-0.5 rounded text-xs ${config.enabled
                                        ? "bg-green-100 text-green-700"
                                        : "bg-gray-100 text-gray-600"
                                    }`}
                            >
                                {config.enabled ? "Enabled" : "Disabled"}
                            </span>
                        </div>
                        <p className="text-sm text-text-subtle mt-1">
                            Client ID: {config.client_id ? config.client_id.slice(0, 20) + "..." : "Not configured"}
                        </p>
                        <p className="text-xs text-text-subtle mt-1">
                            Redirect URI: {config.redirect_uri}
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={onToggle}
                            className={`p-2 rounded hover:bg-background-subtle ${config.enabled ? "text-green-600" : "text-gray-400"
                                }`}
                            title={config.enabled ? "Disable" : "Enable"}
                        >
                            {config.enabled ? <MdCheck /> : <MdClose />}
                        </button>
                        <button
                            onClick={onEdit}
                            className="p-2 rounded hover:bg-background-subtle"
                            title="Edit"
                        >
                            <MdEdit />
                        </button>
                        <button
                            onClick={onDelete}
                            className="p-2 rounded hover:bg-background-subtle text-red-500"
                            title="Delete"
                        >
                            <MdDelete />
                        </button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

function OAuthConfigForm({
    config,
    onSave,
    onCancel,
}: {
    config: OAuthConfig | null;
    onSave: (config: OAuthConfigInput) => void;
    onCancel: () => void;
}) {
    const [formData, setFormData] = useState<OAuthConfigInput>({
        provider: config?.provider || "",
        client_id: config?.client_id || "",
        client_secret: "",
        redirect_uri: config?.redirect_uri || "",
        enabled: config?.enabled ?? true,
    });
    const [isSaving, setIsSaving] = useState(false);

    const handleSubmit = async () => {
        setIsSaving(true);
        await onSave(formData);
        setIsSaving(false);
    };

    return (
        <Card className="shadow-md">
            <CardHeader>
                <CardTitle>{config ? "Edit" : "Add"} OAuth Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="provider">Provider</Label>
                    <select
                        id="provider"
                        value={formData.provider}
                        onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                        className="w-full px-3 py-2 border border-border rounded-lg"
                    >
                        <option value="">Select provider...</option>
                        <option value="google_drive">Google Drive</option>
                        <option value="slack">Slack</option>
                        <option value="confluence">Confluence</option>
                        <option value="sharepoint">SharePoint</option>
                        <option value="github">GitHub</option>
                        <option value="jira">Jira</option>
                        <option value="salesforce">Salesforce</option>
                    </select>
                </div>
                <div className="space-y-2">
                    <Label htmlFor="clientId">Client ID</Label>
                    <Input
                        id="clientId"
                        value={formData.client_id}
                        onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                        placeholder="Enter client ID from provider"
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="clientSecret">Client Secret</Label>
                    <Input
                        id="clientSecret"
                        type="password"
                        value={formData.client_secret}
                        onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
                        placeholder={config ? "Leave empty to keep existing" : "Enter client secret"}
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="redirectUri">Redirect URI</Label>
                    <Input
                        id="redirectUri"
                        value={formData.redirect_uri}
                        onChange={(e) => setFormData({ ...formData, redirect_uri: e.target.value })}
                        placeholder="https://your-domain.com/api/oauth/callback/{provider}"
                    />
                    <p className="text-xs text-text-subtle">
                        Add this URL to your OAuth provider&apos;s allowed redirect URIs
                    </p>
                </div>
                <div className="flex gap-2 pt-4">
                    <button
                        onClick={handleSubmit}
                        disabled={isSaving || !formData.provider || !formData.client_id}
                        className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                    >
                        {isSaving && <MdRefresh className="animate-spin" />}
                        Save
                    </button>
                    <button
                        onClick={onCancel}
                        className="px-4 py-2 border border-border rounded-lg hover:bg-background-subtle"
                    >
                        Cancel
                    </button>
                </div>
            </CardContent>
        </Card>
    );
}

export default function OAuthSettingsPage() {
    const [configs, setConfigs] = useState<OAuthConfig[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [editingConfig, setEditingConfig] = useState<OAuthConfig | null>(null);
    const [isAdding, setIsAdding] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadConfigs = async () => {
        setIsLoading(true);
        const data = await fetchOAuthConfigs();
        setConfigs(data);
        setIsLoading(false);
    };

    useEffect(() => {
        loadConfigs();
    }, []);

    const handleToggle = async (config: OAuthConfig) => {
        const success = await toggleOAuthConfig(config.id, !config.enabled);
        if (success) {
            setConfigs(configs.map(c =>
                c.id === config.id ? { ...c, enabled: !c.enabled } : c
            ));
        } else {
            setError("Failed to toggle configuration.");
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this configuration?")) return;

        const success = await deleteOAuthConfig(id);
        if (success) {
            setConfigs(configs.filter(c => c.id !== id));
        } else {
            setError("Failed to delete configuration.");
        }
    };

    const handleSave = async (configData: OAuthConfigInput) => {
        const success = await saveOAuthConfig(configData, editingConfig?.id);
        if (success) {
            await loadConfigs();
            setEditingConfig(null);
            setIsAdding(false);
        } else {
            setError("Failed to save configuration.");
        }
    };

    return (
        <div className="container max-w-4xl">
            <div className="flex justify-between items-center">
                <AdminPageTitle
                    title="OAuth Settings"
                    icon={<MdSecurity size={32} className="my-auto" />}
                />
                <button
                    onClick={() => {
                        setIsAdding(true);
                        setEditingConfig(null);
                    }}
                    className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 flex items-center gap-2"
                >
                    <MdAdd />
                    Add Configuration
                </button>
            </div>

            {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                    <MdWarning />
                    {error}
                    <button onClick={() => setError(null)} className="ml-auto">×</button>
                </div>
            )}

            <div className="space-y-4 mt-6">
                {/* Add/Edit Form */}
                {(isAdding || editingConfig) && (
                    <OAuthConfigForm
                        config={editingConfig}
                        onSave={handleSave}
                        onCancel={() => {
                            setIsAdding(false);
                            setEditingConfig(null);
                        }}
                    />
                )}

                {/* Provider Cards */}
                <Card className="shadow-md">
                    <CardHeader>
                        <CardTitle>Configured Providers</CardTitle>
                        <CardDescription>
                            Manage OAuth configurations for external data sources
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {isLoading ? (
                            <div className="text-center py-8">
                                <MdRefresh className="animate-spin text-2xl mx-auto mb-2" />
                                <p>Loading configurations...</p>
                            </div>
                        ) : configs.length === 0 ? (
                            <p className="text-center text-text-subtle py-8">
                                No OAuth configurations yet. Add your first configuration above.
                            </p>
                        ) : (
                            configs.map((config) => (
                                <OAuthConfigCard
                                    key={config.id}
                                    config={config}
                                    onToggle={() => handleToggle(config)}
                                    onEdit={() => {
                                        setEditingConfig(config);
                                        setIsAdding(false);
                                    }}
                                    onDelete={() => handleDelete(config.id)}
                                />
                            ))
                        )}
                    </CardContent>
                </Card>

                {/* Help Section */}
                <Card className="shadow-sm">
                    <CardContent className="pt-6">
                        <h4 className="font-medium mb-2">Setting up OAuth</h4>
                        <ol className="list-decimal list-inside space-y-1 text-sm text-text-subtle">
                            <li>Register your application with the OAuth provider</li>
                            <li>Copy the Client ID and Client Secret</li>
                            <li>Add the redirect URI to the provider&apos;s allowed list</li>
                            <li>Enter the credentials above and enable the configuration</li>
                        </ol>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
