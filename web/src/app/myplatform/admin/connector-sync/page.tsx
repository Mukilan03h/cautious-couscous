"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgRefresh from "@/icons/refresh-cw";

interface SyncStatus {
    connector_id: number;
    connector_type: string;
    sync_enabled: boolean;
    sync_status: string;
    last_sync_at: string | null;
    last_error: string | null;
}

interface Connector {
    id: number;
    name: string;
    source: string;
}

export default function ConnectorSyncPage() {
    const [selectedConnector, setSelectedConnector] = useState<number | null>(null);
    const [connectorType, setConnectorType] = useState("slack");
    const [isEnabling, setIsEnabling] = useState(false);

    // This would fetch from your connectors API
    const { data: connectors } = useSWR<Connector[]>(
        "/api/manage/admin/connector",
        errorHandlingFetcher
    );

    const { data: syncStatus, mutate: refreshStatus } = useSWR<SyncStatus | null>(
        selectedConnector
            ? `/api/admin/connector-sync/${selectedConnector}`
            : null,
        errorHandlingFetcher
    );

    const handleEnableSync = async () => {
        if (!selectedConnector) return;
        setIsEnabling(true);
        try {
            const res = await fetch("/api/admin/connector-sync/enable", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    connector_id: selectedConnector,
                    connector_type: connectorType,
                }),
            });
            if (res.ok) {
                refreshStatus();
            }
        } finally {
            setIsEnabling(false);
        }
    };

    const handleTriggerSync = async () => {
        if (!selectedConnector) return;
        const res = await fetch(
            `/api/admin/connector-sync/${selectedConnector}/trigger`,
            { method: "POST" }
        );
        if (res.ok) {
            refreshStatus();
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case "success":
                return "text-green-600 bg-green-100";
            case "error":
                return "text-red-600 bg-red-100";
            case "syncing":
            case "pending":
                return "text-yellow-600 bg-yellow-100";
            default:
                return "text-gray-600 bg-gray-100";
        }
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Connector Permission Sync" icon={SvgRefresh} />

            <Text className="mb-4">
                Sync permissions from external data sources (Slack, Google Drive,
                SharePoint, etc.) to control document access.
            </Text>

            <div className="grid grid-cols-3 gap-6">
                {/* Connector Selection */}
                <div className="col-span-1 border rounded-lg p-4">
                    <h3 className="font-medium mb-3">Select Connector</h3>
                    <div className="space-y-2">
                        {connectors?.map((connector) => (
                            <button
                                key={connector.id}
                                onClick={() => {
                                    setSelectedConnector(connector.id);
                                    setConnectorType(connector.source);
                                }}
                                className={`w-full text-left p-3 rounded border ${selectedConnector === connector.id
                                    ? "border-blue-600 bg-blue-50"
                                    : "hover:bg-gray-50"
                                    }`}
                            >
                                <p className="font-medium">{connector.name}</p>
                                <p className="text-sm text-gray-500">
                                    {connector.source}
                                </p>
                            </button>
                        ))}
                        {(!connectors || connectors.length === 0) && (
                            <p className="text-gray-500 text-sm">
                                No connectors configured
                            </p>
                        )}
                    </div>
                </div>

                {/* Sync Status and Controls */}
                <div className="col-span-2 border rounded-lg p-4">
                    {selectedConnector ? (
                        <>
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="font-medium">Permission Sync Status</h3>
                                <div className="flex gap-2">
                                    {!syncStatus?.sync_enabled && (
                                        <button
                                            onClick={handleEnableSync}
                                            disabled={isEnabling}
                                            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                                        >
                                            {isEnabling ? "Enabling..." : "Enable Sync"}
                                        </button>
                                    )}
                                    {syncStatus?.sync_enabled && (
                                        <button
                                            onClick={handleTriggerSync}
                                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                        >
                                            Trigger Sync Now
                                        </button>
                                    )}
                                </div>
                            </div>

                            {syncStatus ? (
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <span className="text-sm text-gray-500">
                                                Connector Type
                                            </span>
                                            <p className="font-medium capitalize">
                                                {syncStatus.connector_type}
                                            </p>
                                        </div>
                                        <div>
                                            <span className="text-sm text-gray-500">
                                                Sync Enabled
                                            </span>
                                            <p className="font-medium">
                                                {syncStatus.sync_enabled ? "Yes" : "No"}
                                            </p>
                                        </div>
                                        <div>
                                            <span className="text-sm text-gray-500">
                                                Status
                                            </span>
                                            <p>
                                                <span
                                                    className={`px-2 py-1 rounded text-sm ${getStatusColor(
                                                        syncStatus.sync_status
                                                    )}`}
                                                >
                                                    {syncStatus.sync_status}
                                                </span>
                                            </p>
                                        </div>
                                        <div>
                                            <span className="text-sm text-gray-500">
                                                Last Sync
                                            </span>
                                            <p className="font-medium">
                                                {syncStatus.last_sync_at
                                                    ? new Date(
                                                        syncStatus.last_sync_at
                                                    ).toLocaleString()
                                                    : "Never"}
                                            </p>
                                        </div>
                                    </div>

                                    {syncStatus.last_error && (
                                        <div className="p-3 bg-red-50 border border-red-200 rounded">
                                            <span className="text-sm font-medium text-red-700">
                                                Last Error:
                                            </span>
                                            <p className="text-red-600 text-sm mt-1">
                                                {syncStatus.last_error}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="p-4 bg-gray-50 rounded">
                                    <p className="text-gray-600">
                                        Permission sync is not enabled for this connector.
                                        Click &quot;Enable Sync&quot; to start syncing permissions
                                        from the source system.
                                    </p>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="flex items-center justify-center h-48 text-gray-500">
                            Select a connector to view sync status
                        </div>
                    )}
                </div>
            </div>

            {/* Info Section */}
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-700 mb-2">
                    About Permission Sync
                </h4>
                <p className="text-blue-600 text-sm">
                    Permission sync automatically imports access controls from your
                    connected data sources. When enabled, only users with access to
                    documents in the source system (e.g., Slack channels, Google Drive
                    folders) will be able to query those documents in ESA.
                </p>
            </div>
        </div>
    );
}
