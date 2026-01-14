import { useQuery, useMutation } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Loader2, Play, Users, Settings2, Plus, Trash2, Activity, Database, RefreshCw, Eraser, FileText } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { toast } from "sonner"

import { CrawlerService, OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export const Route = createFileRoute("/_layout/crawler/manual")({
    component: ManualCrawlerPage,
})

interface CrawlerTaskStatus {
    id: string;
    status: "pending" | "processing" | "paused" | "completed" | "failed";
    current_phase?: "scout" | "architect" | "review" | "harvester" | "refinery" | "completed" | "failed";
    pipeline_state?: string | any;
    items_harvested?: number;
    result_sql_content?: string;
}

function ManualCrawlerPage() {
    const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
    const [logs, setLogs] = useState<string[]>([])
    const terminalRef = useRef<HTMLDivElement>(null)

    // Config State
    const [url, setUrl] = useState("https://books.toscrape.com/")
    const [tableName, setTableName] = useState("products")
    const [columns, setColumns] = useState<string[]>(["title", "price", "description", "category"])
    const [newColumn, setNewColumn] = useState("")
    const [maxPages, setMaxPages] = useState(1)
    const [concurrency, setConcurrency] = useState(5)

    // Polling query
    const { data: taskStatus, refetch: refetchStatus } = useQuery<CrawlerTaskStatus>({
        queryKey: ["crawler-manual", currentTaskId],
        queryFn: () => CrawlerService.getCrawlStatus({ taskId: currentTaskId! }),
        enabled: !!currentTaskId,
        refetchInterval: (query) => {
            const status = query.state.data?.status
            if (status === "completed" || status === "failed") {
                return false // Stop polling
            }
            return 1000 // Poll every 1 second
        },
    })

    // Auto-scroll terminal
    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight
        }
    }, [logs, taskStatus])

    // Watch status for Phase updates (Manual mode might skip phases but still good to see errors)
    useEffect(() => {
        if (taskStatus) {
            let state: any = null;
            if (taskStatus.pipeline_state) {
                try {
                    state = typeof taskStatus.pipeline_state === 'string'
                        ? JSON.parse(taskStatus.pipeline_state)
                        : taskStatus.pipeline_state;
                } catch (e) {
                    console.error("Failed to parse pipeline state", e);
                }
            }

            // Sync logs from pipeline_state if available
            if (state && state.logs && Array.isArray(state.logs)) {
                if (JSON.stringify(state.logs) !== JSON.stringify(logs)) {
                    setLogs(state.logs)
                }
            }
        }
    }, [taskStatus])

    const startMutation = useMutation({
        mutationFn: CrawlerService.startCrawl,
        onSuccess: (taskId) => {
            setCurrentTaskId(taskId)
            setLogs(prev => [...prev, `[System] Task started: ${taskId}`])
            toast.success("Manual scrape started")
        },
        onError: (err) => {
            toast.error("Failed to start scraper")
            console.error(err)
        }
    })

    const handleStartCrawl = () => {
        if (!url) {
            toast.error("Please enter a URL")
            return
        }
        setLogs([])
        startMutation.mutate({
            requestBody: {
                url,
                table_name: tableName || undefined,
                columns: columns,
                max_pages: maxPages,
                concurrency,
                mode: "manual"
            }
        })
    }

    const handleAddColumn = () => {
        if (newColumn.trim()) {
            if (columns.includes(newColumn.trim())) {
                toast.error("Column already exists")
                return
            }
            setColumns([...columns, newColumn.trim()])
            setNewColumn("")
        }
    }

    const handleRemoveColumn = (colToRemove: string) => {
        setColumns(columns.filter(col => col !== colToRemove))
    }

    const handleDownload = async (fileType: 'csv' | 'sql') => {
        if (!currentTaskId) return
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const headers: Record<string, string> = {}
            if (typeof token === 'string') headers['Authorization'] = `Bearer ${token}`
            const baseUrl = OpenAPI.BASE || "";
            const response = await fetch(`${baseUrl}/api/v1/crawl/download/${currentTaskId}/${fileType}`, {
                method: 'GET',
                headers
            })
            if (!response.ok) throw new Error('Download failed')
            const blob = await response.blob()
            const downloadUrl = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = downloadUrl
            a.download = fileType === 'csv' ? `crawler_data_${currentTaskId}.csv` : `generated_sql_${currentTaskId}.sql`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(downloadUrl)
            document.body.removeChild(a)
            toast.success(`${fileType.toUpperCase()} file downloaded`)
        } catch (error) {
            console.error(error)
            toast.error(`Failed to download ${fileType.toUpperCase()} file`)
        }
    }

    return (
        <div className="container mx-auto py-10 max-w-6xl space-y-8">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                    <Users className="w-8 h-8 text-primary" />
                    Manual Scraper
                </h1>
                <p className="text-muted-foreground">
                    手动定义规则的直接数据采集工具。
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
                                <Label htmlFor="url-manual" className="flex items-center gap-2">
                                    <Activity className="w-3.5 h-3.5" />
                                    目标 URL
                                </Label>
                                <Input
                                    id="url-manual"
                                    placeholder="https://books.toscrape.com/"
                                    value={url}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="table-manual" className="flex items-center gap-2">
                                    <Database className="w-3.5 h-3.5" />
                                    表名
                                </Label>
                                <Input
                                    id="table-manual"
                                    placeholder="products"
                                    value={tableName}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTableName(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>列名</Label>
                                <div className="flex gap-2">
                                    <Input
                                        placeholder="添加列..."
                                        value={newColumn}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewColumn(e.target.value)}
                                        onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => e.key === "Enter" && handleAddColumn()}
                                    />
                                    <Button variant="outline" size="icon" onClick={handleAddColumn}>
                                        <Plus className="w-4 h-4" />
                                    </Button>
                                </div>
                                <div className="flex flex-wrap gap-2 mt-2">
                                    {columns.map(col => (
                                        <div key={col} className="bg-secondary text-secondary-foreground px-3 py-1 rounded-md text-sm flex items-center gap-2">
                                            {col}
                                            <button onClick={() => handleRemoveColumn(col)} className="text-muted-foreground hover:text-destructive">
                                                <Trash2 className="w-3 h-3" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="maxPages">最大页数</Label>
                                    <Input
                                        id="maxPages"
                                        type="number"
                                        min={1}
                                        value={maxPages}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMaxPages(parseInt(e.target.value) || 1)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="concurrency">并发数</Label>
                                    <Input
                                        id="concurrency"
                                        type="number"
                                        min={1}
                                        max={20}
                                        value={concurrency}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConcurrency(parseInt(e.target.value) || 1)}
                                    />
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter>
                            <Button
                                size="lg"
                                onClick={handleStartCrawl}
                                disabled={startMutation.isPending || (taskStatus?.status === "processing")}
                                className="w-full"
                            >
                                {startMutation.isPending ? (
                                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                ) : (
                                    <Play className="mr-2 h-5 w-5" />
                                )}
                                开始爬取
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
                                    实时终端
                                </CardTitle>
                                <div className="flex items-center gap-2">
                                    <div className="text-xs text-slate-400 mr-2">
                                        任务 ID: {currentTaskId || "等待中..."}
                                    </div>
                                    <Button variant="ghost" size="icon" className="h-6 w-6 text-slate-400 hover:text-slate-100" onClick={() => refetchStatus()}>
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
                                {taskStatus?.items_harvested !== undefined && (
                                    <div className="text-blue-400 font-bold">
                                        {`> 已捕获数据条数: ${taskStatus.items_harvested}`}
                                    </div>
                                )}
                                {taskStatus?.status === 'failed' && (
                                    <div className="text-red-400 mt-2">
                                        {`> 错误: 执行失败。请查看日志。`}
                                    </div>
                                )}
                                {!currentTaskId && (
                                    <div className="text-slate-600 italic">等待启动...</div>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Results Actions */}
                    <div className="flex gap-4">
                        <Button
                            onClick={() => handleDownload('csv')}
                            className="flex-1"
                            variant="outline"
                            disabled={taskStatus?.status !== "completed"}
                        >
                            <FileText className="mr-2 h-4 w-4" /> 下载 CSV
                        </Button>
                        <Button
                            onClick={() => handleDownload('sql')}
                            className="flex-1"
                            variant="outline"
                            disabled={taskStatus?.status !== "completed"}
                        >
                            <Database className="mr-2 h-4 w-4" /> 下载 SQL
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ManualCrawlerPage
