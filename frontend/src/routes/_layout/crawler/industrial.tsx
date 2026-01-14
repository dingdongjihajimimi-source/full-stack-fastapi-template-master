import { useMutation } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Loader2, Play, Activity, Database, Settings2, Eye, FileDown, Trash2, Home, Bot, RefreshCw, Eraser } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { toast } from "sonner"

import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"

export const Route = createFileRoute("/_layout/crawler/industrial")({
    component: IndustrialCrawlerPage,
})

interface Batch {
    id: string;
    created_at: string;
    item_count: number;
    url: string;
    status: string;
    storage_path?: string;
}

interface BatchFile {
    name: string;
    size: number;
    url: string;
    content_type: string;
    timestamp: string;
}

const HARVEST_STRATEGIES = {
    recon: { label: "🚀 快速侦察 (Recon)", scroll: 1, items: 20, wait: "domcontentloaded" },
    standard: { label: "🏬 标准收割 (Standard)", scroll: 5, items: 100, wait: "networkidle" },
    deep: { label: "🌊 深度挖掘 (Deep Dive)", scroll: 20, items: 500, wait: "networkidle" },
    custom: { label: "🔧 自定义 (Custom)", scroll: 5, items: 100, wait: "networkidle" },
}

function IndustrialCrawlerPage() {
    const [strategy, setStrategy] = useState<keyof typeof HARVEST_STRATEGIES>("standard")
    const [scrollCount, setScrollCount] = useState(HARVEST_STRATEGIES.standard.scroll)
    const [maxItems, setMaxItems] = useState(HARVEST_STRATEGIES.standard.items)
    const [waitUntil, setWaitUntil] = useState<"domcontentloaded" | "load" | "networkidle">(HARVEST_STRATEGIES.standard.wait as "domcontentloaded" | "load" | "networkidle")
    const [url, setUrl] = useState("https://books.toscrape.com/")

    const [batches, setBatches] = useState<Batch[]>([])
    // Track previous batches for log diffing
    const prevBatchesRef = useRef<Batch[]>([]);
    const [logs, setLogs] = useState<string[]>([])
    const terminalRef = useRef<HTMLDivElement>(null)

    const [selectedBatchFiles, setSelectedBatchFiles] = useState<BatchFile[]>([])
    const [isFilesDialogOpen, setIsFilesDialogOpen] = useState(false)
    const [currentBatchId, setCurrentBatchId] = useState<string | null>(null)
    const [isAdvancedOpen, setIsAdvancedOpen] = useState(false)

    // Auto-scroll terminal
    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight
        }
    }, [logs])

    const handleStrategyChange = (val: keyof typeof HARVEST_STRATEGIES) => {
        setStrategy(val)
        if (val !== 'custom') {
            const config = HARVEST_STRATEGIES[val]
            setScrollCount(config.scroll)
            setMaxItems(config.items)
            setWaitUntil(config.wait as any)
        }
    }

    const fetchBatches = async () => {
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const res = await fetch(`${baseUrl}/api/v1/industrial/batches`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (res.ok) {
                const data = await res.json();
                setBatches(data);
            }
        } catch (e) {
            console.error("Failed to fetch batches", e);
        }
    }

    useEffect(() => {
        fetchBatches();
        const interval = setInterval(fetchBatches, 2000); // Polling faster for smoother logs
        return () => clearInterval(interval);
    }, []);

    // Log Streaming Logic (Phase 12)
    useEffect(() => {
        const newLogs: string[] = [];
        const prevBatches = prevBatchesRef.current;

        batches.forEach(batch => {
            const prev = prevBatches.find(p => p.id === batch.id);

            // New Batch detected
            if (!prev) {
                // Don't log old completed batches on first load, only log pending/processing or recent ones
                const isRecent = (new Date().getTime() - new Date(batch.created_at).getTime()) < 60000;
                if (isRecent || batch.status === 'processing') {
                    newLogs.push(`[System] New Batch Detected: ${batch.id.slice(0, 8)} [Goal: ${batch.url}]`);
                }
                return;
            }

            // Status Changed
            if (prev.status !== batch.status) {
                let msg = `[Status] Batch ${batch.id.slice(0, 8)}: ${prev.status} -> ${batch.status}`;
                if (batch.status === 'completed') msg = `[Success] Batch ${batch.id.slice(0, 8)} completed. Harvested ${batch.item_count} items.`;
                if (batch.status === 'captcha_blocked') msg = `[Warning] Batch ${batch.id.slice(0, 8)} stopped by CAPTCHA protection.`;
                if (batch.status === 'failed') msg = `[Error] Batch ${batch.id.slice(0, 8)} failed unexpectedly.`;
                newLogs.push(msg);
            }

            // Item Count Incremented
            if (batch.item_count > prev.item_count) {
                const diff = batch.item_count - prev.item_count;
                newLogs.push(`[Harvest] Batch ${batch.id.slice(0, 8)} captured +${diff} items (Total: ${batch.item_count}).`);
            }
        });

        if (newLogs.length > 0) {
            setLogs(prev => [...prev, ...newLogs]);
        }

        prevBatchesRef.current = batches;
    }, [batches]);

    const startIndustrialMutation = useMutation({
        mutationFn: async () => {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const res = await fetch(`${baseUrl}/api/v1/industrial/collect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({
                    url,
                    scroll_count: scrollCount,
                    max_items: maxItems,
                    wait_until: waitUntil
                })
            });
            if (!res.ok) throw new Error("Failed to start");
            return res.json();
        },
        onSuccess: (batchId) => {
            toast.success("Industrial harvest started");
            setLogs(prev => [...prev, `[System] Industrial Harvest started. Batch ID: ${batchId}`]);
            fetchBatches();
        },
        onError: () => toast.error("Failed to start harvest")
    });


    const handleViewFiles = async (batchId: string) => {
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const res = await fetch(`${baseUrl}/api/v1/industrial/batch/${batchId}/files`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (res.ok) {
                const data = await res.json();
                setSelectedBatchFiles(data);
                setCurrentBatchId(batchId);
                setIsFilesDialogOpen(true);
            }
        } catch (e) {
            toast.error("Failed to fetch files");
        }
    }

    const handleDownloadBatch = async (batchId: string) => {
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const response = await fetch(`${baseUrl}/api/v1/industrial/download/${batchId}`, {
                method: 'GET',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) throw new Error('Download failed');
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `industrial_batch_${batchId.slice(0, 8)}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
            toast.success("ZIP downloaded");
        } catch (e) {
            console.error(e);
            toast.error("Failed to download ZIP");
        }
    }

    const handleDownloadSingleFile = async (batchId: string, filename: string) => {
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const response = await fetch(`${baseUrl}/api/v1/industrial/batch/${batchId}/file/${filename}`, {
                method: 'GET',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) throw new Error('Download failed');
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
        } catch (e) {
            toast.error("Failed to download file");
        }
    }

    const handleDeleteBatch = async (batchId: string) => {
        if (!confirm("Are you sure you want to delete this batch and all its files?")) return;
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const res = await fetch(`${baseUrl}/api/v1/industrial/batch/${batchId}`, {
                method: 'DELETE',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (res.ok) {
                toast.success("Batch deleted");
                fetchBatches();
            }
        } catch (e) {
            toast.error("Failed to delete batch");
        }
    }

    return (
        <div className="container mx-auto py-10 max-w-6xl space-y-8">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                    <Home className="w-8 h-8 text-primary" />
                    Industrial Harvest
                </h1>
                <p className="text-muted-foreground">
                    生产级大规模数据收割终端。支持混合存储、去重与实时监控。
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-12">
                {/* Left Column: Config */}
                <div className="md:col-span-4 space-y-6">
                    <Card className="h-full">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Settings2 className="w-5 h-5" />
                                配置
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="url-ind" className="flex items-center gap-2">
                                    <Activity className="w-3.5 h-3.5" />
                                    目标 URL
                                </Label>
                                <Input
                                    id="url-ind"
                                    placeholder="https://books.toscrape.com/"
                                    value={url}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label className="flex items-center gap-2">
                                    <Bot className="w-3.5 h-3.5" />
                                    收割策略 (Harvest Strategy)
                                </Label>
                                <Select value={strategy} onValueChange={(v: any) => handleStrategyChange(v)}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="选择收割模式" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {Object.entries(HARVEST_STRATEGIES).map(([id, config]) => (
                                            <SelectItem key={id} value={id}>
                                                {config.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-4 border rounded-lg p-3 bg-muted/30">
                                <div className="flex items-center justify-between">
                                    <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                                        <Settings2 className="w-3 h-3" />
                                        高级配置 (Advanced)
                                    </Label>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 text-[10px]"
                                        onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
                                    >
                                        {isAdvancedOpen ? "收起" : "展开"}
                                    </Button>
                                </div>

                                {isAdvancedOpen && (
                                    <div className="grid grid-cols-2 gap-4 pt-2 border-t animate-in fade-in slide-in-from-top-1 duration-200">
                                        <div className="space-y-1.5">
                                            <Label htmlFor="scroll-ind" className="text-[11px]">滑动次数</Label>
                                            <Input
                                                id="scroll-ind"
                                                type="number"
                                                className="h-8 text-xs"
                                                value={scrollCount}
                                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                                    setScrollCount(parseInt(e.target.value) || 1);
                                                    setStrategy('custom');
                                                }}
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label htmlFor="items-ind" className="text-[11px]">采集上限 (条)</Label>
                                            <Input
                                                id="items-ind"
                                                type="number"
                                                className="h-8 text-xs"
                                                value={maxItems}
                                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                                    setMaxItems(parseInt(e.target.value) || 1);
                                                    setStrategy('custom');
                                                }}
                                            />
                                        </div>
                                        <div className="space-y-1.5 col-span-2">
                                            <Label className="text-[11px]">等待条件 (Wait Until)</Label>
                                            <Select
                                                value={waitUntil}
                                                onValueChange={(v: any) => {
                                                    setWaitUntil(v);
                                                    setStrategy('custom');
                                                }}
                                            >
                                                <SelectTrigger className="h-8 text-xs">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="domcontentloaded">DOM 加载完成</SelectItem>
                                                    <SelectItem value="load">全页面加载</SelectItem>
                                                    <SelectItem value="networkidle">网络空闲 (推荐)</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="mt-4 border rounded-md p-2 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm flex flex-col h-[320px]">
                                <h3 className="text-sm font-medium mb-2 flex items-center gap-2 px-2 pt-2">
                                    <Database className="w-4 h-4 text-blue-500" />
                                    Data Lake Ingestion Queue
                                    <span className="ml-auto text-xs text-muted-foreground font-normal">
                                        {batches.length} batches
                                    </span>
                                </h3>
                                <div className="flex-1 overflow-y-auto custom-scrollbar">
                                    <table className="w-full text-xs">
                                        <thead className="bg-muted text-muted-foreground sticky top-0">
                                            <tr>
                                                <th className="p-2 text-left">Batch ID</th>
                                                <th className="p-2 text-left">Items</th>
                                                <th className="p-2 text-left">Time</th>
                                                <th className="p-2 text-left">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                            {batches.length === 0 ? (
                                                <tr><td colSpan={5} className="p-8 text-center text-muted-foreground italic">No batches found in the data lake.</td></tr>
                                            ) : (
                                                batches.map(b => (
                                                    <tr key={b.id} className="group hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                                                        <td className="p-3 font-mono text-xs text-muted-foreground group-hover:text-primary transition-colors">
                                                            <div className="flex items-center gap-2">
                                                                <Database className="w-3 h-3 opacity-50" />
                                                                {b.id.slice(0, 8)}
                                                            </div>
                                                        </td>
                                                        <td className="p-3">
                                                            <div className="flex flex-col gap-1">
                                                                <span className="flex items-center gap-2 font-medium">
                                                                    {b.item_count.toLocaleString()} <span className="text-[10px] text-muted-foreground font-normal">items</span>
                                                                    {b.status === 'processing' && (
                                                                        <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                                                                    )}
                                                                </span>
                                                                <div className="flex items-center gap-1.5">
                                                                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-bold shadow-sm ${b.status === 'processing' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 animate-pulse' :
                                                                            b.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                                                                b.status === 'captcha_blocked' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                                                                    b.status === 'failed' ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400' :
                                                                                        'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                                                        }`}>
                                                                        {b.status === 'processing' ? 'Harvesting' :
                                                                            b.status === 'captcha_blocked' ? 'Blocked' :
                                                                                b.status}
                                                                    </span>
                                                                    {b.item_count > 0 && (
                                                                        <span className="text-[10px] text-muted-foreground bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded-full flex items-center gap-1">
                                                                            <span className="w-1 h-1 rounded-full bg-emerald-500"></span>
                                                                            Hybrid
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td className="p-3">
                                                            <div className="flex flex-col text-xs">
                                                                <span className="text-slate-700 dark:text-slate-300 font-medium">
                                                                    {new Date(b.created_at).toLocaleDateString()}
                                                                </span>
                                                                <span className="text-muted-foreground text-[10px]">
                                                                    {new Date(b.created_at).toLocaleTimeString()}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className="p-3">
                                                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                                <Button size="sm" variant="secondary" className="h-7 text-xs px-3 shadow-none hover:bg-white hover:shadow-sm dark:hover:bg-slate-800" onClick={() => handleViewFiles(b.id)}>
                                                                    <Eye className="w-3.5 h-3.5 mr-1.5" />
                                                                    Files
                                                                </Button>
                                                                <Button size="sm" variant="ghost" className="h-7 w-7 p-0 rounded-full hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/30 dark:hover:text-blue-400 transition-colors" onClick={() => handleDownloadBatch(b.id)} title="Download Archive">
                                                                    <FileDown className="w-3.5 h-3.5" />
                                                                </Button>
                                                                <Button size="sm" variant="ghost" className="h-7 w-7 p-0 rounded-full hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors" onClick={() => handleDeleteBatch(b.id)} title="Purge Data">
                                                                    <Trash2 className="w-3.5 h-3.5" />
                                                                </Button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter>
                            <Button
                                size="lg"
                                onClick={() => startIndustrialMutation.mutate()}
                                disabled={startIndustrialMutation.isPending}
                                className="w-full"
                            >
                                {startIndustrialMutation.isPending ? (
                                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                ) : (
                                    <Play className="mr-2 h-5 w-5" />
                                )}
                                开始收割
                            </Button>
                        </CardFooter>
                    </Card>
                </div>

                {/* Right Column: Visualization & Logs */}
                <div className="md:col-span-8 space-y-6">
                    {/* Logs / Console */}
                    <Card className="flex-1 min-h-[400px] flex flex-col bg-slate-950 text-slate-50 border-slate-800">
                        <CardHeader className="py-3 border-b border-slate-800">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-mono flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                    实时终端 (Live Stream)
                                </CardTitle>
                                <div className="flex items-center gap-2">
                                    <Button variant="ghost" size="icon" className="h-6 w-6 text-slate-400 hover:text-slate-100" onClick={() => fetchBatches()}>
                                        <RefreshCw className="w-3 h-3" />
                                    </Button>
                                    <Button variant="ghost" size="icon" className="h-6 w-6 text-slate-400 hover:text-slate-100" onClick={() => setLogs([])}>
                                        <Eraser className="w-3 h-3" />
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="flex-1 p-0 min-h-0 flex flex-col">
                            <div
                                ref={terminalRef}
                                className="flex-1 p-4 font-mono text-xs overflow-y-auto max-h-[400px] space-y-1"
                            >
                                {logs.map((log, i) => (
                                    <div key={i} className="break-all opacity-80 hover:opacity-100">
                                        <span className="text-slate-500 mr-2">[{new Date().toLocaleTimeString()}]</span>
                                        {log}
                                    </div>
                                ))}
                                {logs.length === 0 && (
                                    <div className="text-slate-600 italic">等待数据收割任务...</div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Files Dialog */}
            <Dialog open={isFilesDialogOpen} onOpenChange={setIsFilesDialogOpen}>
                <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
                    <DialogHeader>
                        <DialogTitle>Batch Files: {currentBatchId?.slice(0, 8)}</DialogTitle>
                        <DialogDescription>
                            Direct file capture from Industrial Harvest. Total {selectedBatchFiles.length} items.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto mt-4 border rounded-md">
                        <table className="w-full text-sm">
                            <thead className="bg-muted sticky top-0">
                                <tr>
                                    <th className="p-2 text-left">Filename</th>
                                    <th className="p-2 text-left">Type</th>
                                    <th className="p-2 text-left">Size</th>
                                    <th className="p-2 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {selectedBatchFiles.map((file) => (
                                    <tr key={file.name} className="hover:bg-muted/50 transition-colors">
                                        <td className="p-2 font-mono text-xs truncate max-w-[300px]" title={file.url}>
                                            {file.name}
                                        </td>
                                        <td className="p-2">
                                            <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${file.content_type.includes('json') ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'
                                                }`}>
                                                {file.content_type.split('_')[0].toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="p-2 text-xs text-muted-foreground">
                                            {(file.size / 1024).toFixed(1)} KB
                                        </td>
                                        <td className="p-2 text-right">
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                className="h-7 w-7 p-0"
                                                onClick={() => handleDownloadSingleFile(currentBatchId!, file.name)}
                                            >
                                                <FileDown className="w-4 h-4" />
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setIsFilesDialogOpen(false)}>Close</Button>
                        <Button onClick={() => handleDownloadBatch(currentBatchId!)}>
                            <FileDown className="w-4 h-4 mr-2" />
                            Download All (ZIP)
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

export default IndustrialCrawlerPage
