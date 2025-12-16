"use client";

import { useEffect, useState, useRef } from "react";
import { AdminPageTitle } from "@/components/admin/Title";
import { MdBrush, MdUpload, MdRefresh, MdWarning, MdCheck } from "react-icons/md";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface WhitelabelSettings {
    application_name: string;
    custom_header_logo_file: string | null;
    custom_logotype: string | null;
    custom_header_content: string;
    custom_popup_header: string;
    custom_popup_content: string;
    enable_consent_popup: boolean;
    custom_lower_disclaimer_content: string;
}

async function fetchSettings(): Promise<WhitelabelSettings | null> {
    try {
        const response = await fetch("/api/myplatform/enterprise-settings", {
            credentials: "include",
        });
        if (!response.ok) return null;
        return await response.json();
    } catch (error) {
        console.error("Error fetching settings:", error);
        return null;
    }
}

async function saveSettings(settings: Partial<WhitelabelSettings>): Promise<boolean> {
    try {
        const response = await fetch("/api/myplatform/admin/enterprise-settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(settings),
        });
        return response.ok;
    } catch (error) {
        console.error("Error saving settings:", error);
        return false;
    }
}

async function uploadLogo(file: File, type: "logo" | "logotype"): Promise<boolean> {
    try {
        const formData = new FormData();
        formData.append("file", file);

        const endpoint = type === "logo"
            ? "/api/myplatform/admin/enterprise-settings/logo"
            : "/api/myplatform/admin/enterprise-settings/logotype";

        const response = await fetch(endpoint, {
            method: "PUT",
            credentials: "include",
            body: formData,
        });
        return response.ok;
    } catch (error) {
        console.error("Error uploading logo:", error);
        return false;
    }
}

export default function WhitelabelingPage() {
    const [settings, setSettings] = useState<WhitelabelSettings | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [saveSuccess, setSaveSuccess] = useState(false);
    const logoInputRef = useRef<HTMLInputElement>(null);
    const logotypeInputRef = useRef<HTMLInputElement>(null);

    const loadSettings = async () => {
        setIsLoading(true);
        setError(null);
        const data = await fetchSettings();
        if (data) {
            setSettings(data);
        } else {
            // Initialize with defaults if no settings exist
            setSettings({
                application_name: "MyPlatform",
                custom_header_logo_file: null,
                custom_logotype: null,
                custom_header_content: "",
                custom_popup_header: "",
                custom_popup_content: "",
                enable_consent_popup: false,
                custom_lower_disclaimer_content: "",
            });
        }
        setIsLoading(false);
    };

    useEffect(() => {
        loadSettings();
    }, []);

    const handleSave = async () => {
        if (!settings) return;

        setIsSaving(true);
        setSaveSuccess(false);

        const success = await saveSettings(settings);
        if (success) {
            setSaveSuccess(true);
            setTimeout(() => setSaveSuccess(false), 3000);
        } else {
            setError("Failed to save settings. Please try again.");
        }

        setIsSaving(false);
    };

    const handleLogoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsSaving(true);
        const success = await uploadLogo(file, "logo");
        if (success) {
            await loadSettings();
        } else {
            setError("Failed to upload logo.");
        }
        setIsSaving(false);
    };

    const handleLogotypeUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsSaving(true);
        const success = await uploadLogo(file, "logotype");
        if (success) {
            await loadSettings();
        } else {
            setError("Failed to upload logotype.");
        }
        setIsSaving(false);
    };

    if (isLoading) {
        return (
            <div className="container max-w-4xl">
                <AdminPageTitle title="Whitelabeling" icon={<MdBrush size={32} className="my-auto" />} />
                <Card className="shadow-md mt-6">
                    <CardContent className="py-12">
                        <div className="flex flex-col items-center justify-center">
                            <MdRefresh className="animate-spin text-4xl mb-4" />
                            <p>Loading settings...</p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="container max-w-4xl">
            <AdminPageTitle
                title="Whitelabeling"
                icon={<MdBrush size={32} className="my-auto" />}
            />

            {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                    <MdWarning />
                    {error}
                    <button onClick={() => setError(null)} className="ml-auto">×</button>
                </div>
            )}

            {saveSuccess && (
                <div className="mt-4 p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-2">
                    <MdCheck />
                    Settings saved successfully!
                </div>
            )}

            <div className="space-y-8 mt-6">
                {/* Branding */}
                <Card className="shadow-md">
                    <CardHeader>
                        <CardTitle>Branding</CardTitle>
                        <CardDescription>Customize your application&apos;s appearance</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="appName">Application Name</Label>
                            <Input
                                id="appName"
                                value={settings?.application_name || ""}
                                onChange={(e) => setSettings(s => s ? { ...s, application_name: e.target.value } : null)}
                                placeholder="Your Application Name"
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Logo Upload */}
                <Card className="shadow-md">
                    <CardHeader>
                        <CardTitle>Logo</CardTitle>
                        <CardDescription>Upload a custom logo (recommended: 200x50px PNG)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-4">
                            <div className="w-48 h-12 border border-dashed border-border rounded-lg flex items-center justify-center bg-background-subtle">
                                {settings?.custom_header_logo_file ? (
                                    <img
                                        src={`/api/myplatform/enterprise-settings/logo`}
                                        alt="Custom Logo"
                                        className="max-h-full max-w-full object-contain"
                                    />
                                ) : (
                                    <span className="text-sm text-text-subtle">No logo uploaded</span>
                                )}
                            </div>
                            <input
                                ref={logoInputRef}
                                type="file"
                                accept="image/*"
                                onChange={handleLogoUpload}
                                className="hidden"
                            />
                            <button
                                onClick={() => logoInputRef.current?.click()}
                                disabled={isSaving}
                                className="px-4 py-2 border border-border rounded-lg hover:bg-background-subtle flex items-center gap-2 disabled:opacity-50"
                            >
                                <MdUpload />
                                Upload Logo
                            </button>
                        </div>
                    </CardContent>
                </Card>

                {/* Logotype Upload */}
                <Card className="shadow-md">
                    <CardHeader>
                        <CardTitle>Logotype</CardTitle>
                        <CardDescription>Upload a custom logotype/wordmark</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-4">
                            <div className="w-48 h-12 border border-dashed border-border rounded-lg flex items-center justify-center bg-background-subtle">
                                {settings?.custom_logotype ? (
                                    <img
                                        src={`/api/myplatform/enterprise-settings/logotype`}
                                        alt="Custom Logotype"
                                        className="max-h-full max-w-full object-contain"
                                    />
                                ) : (
                                    <span className="text-sm text-text-subtle">No logotype uploaded</span>
                                )}
                            </div>
                            <input
                                ref={logotypeInputRef}
                                type="file"
                                accept="image/*"
                                onChange={handleLogotypeUpload}
                                className="hidden"
                            />
                            <button
                                onClick={() => logotypeInputRef.current?.click()}
                                disabled={isSaving}
                                className="px-4 py-2 border border-border rounded-lg hover:bg-background-subtle flex items-center gap-2 disabled:opacity-50"
                            >
                                <MdUpload />
                                Upload Logotype
                            </button>
                        </div>
                    </CardContent>
                </Card>

                {/* Custom Content */}
                <Card className="shadow-md">
                    <CardHeader>
                        <CardTitle>Custom Content</CardTitle>
                        <CardDescription>Add custom header or disclaimer content</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="headerContent">Header Content (HTML)</Label>
                            <textarea
                                id="headerContent"
                                value={settings?.custom_header_content || ""}
                                onChange={(e) => setSettings(s => s ? { ...s, custom_header_content: e.target.value } : null)}
                                placeholder="<!-- Custom header content -->"
                                className="w-full h-24 p-2 border border-border rounded-lg font-mono text-sm"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="disclaimer">Lower Disclaimer Content</Label>
                            <textarea
                                id="disclaimer"
                                value={settings?.custom_lower_disclaimer_content || ""}
                                onChange={(e) => setSettings(s => s ? { ...s, custom_lower_disclaimer_content: e.target.value } : null)}
                                placeholder="Enter disclaimer text..."
                                className="w-full h-24 p-2 border border-border rounded-lg font-mono text-sm"
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Consent Popup */}
                <Card className="shadow-md">
                    <CardHeader>
                        <CardTitle>Consent Popup</CardTitle>
                        <CardDescription>Configure a consent popup for new users</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                id="enablePopup"
                                checked={settings?.enable_consent_popup || false}
                                onChange={(e) => setSettings(s => s ? { ...s, enable_consent_popup: e.target.checked } : null)}
                                className="w-4 h-4"
                            />
                            <Label htmlFor="enablePopup">Enable consent popup</Label>
                        </div>
                        {settings?.enable_consent_popup && (
                            <>
                                <div className="space-y-2">
                                    <Label htmlFor="popupHeader">Popup Header</Label>
                                    <Input
                                        id="popupHeader"
                                        value={settings?.custom_popup_header || ""}
                                        onChange={(e) => setSettings(s => s ? { ...s, custom_popup_header: e.target.value } : null)}
                                        placeholder="Terms & Conditions"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="popupContent">Popup Content</Label>
                                    <textarea
                                        id="popupContent"
                                        value={settings?.custom_popup_content || ""}
                                        onChange={(e) => setSettings(s => s ? { ...s, custom_popup_content: e.target.value } : null)}
                                        placeholder="Enter popup content..."
                                        className="w-full h-32 p-2 border border-border rounded-lg"
                                    />
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>

                {/* Save Button */}
                <div className="flex justify-end">
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                    >
                        {isSaving ? <MdRefresh className="animate-spin" /> : null}
                        {isSaving ? "Saving..." : "Save Changes"}
                    </button>
                </div>
            </div>
        </div>
    );
}
