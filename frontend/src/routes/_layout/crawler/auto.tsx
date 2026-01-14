import { useQuery, useMutation } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Bot, Loader2, Play, Activity, Eye, PlayCircle, Settings2, Code2, RefreshCw, Eraser, FileText, Database } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { toast } from "sonner"

import { CrawlerService, OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

export const Route = createFileRoute("/_layout/crawler/auto")({
    component: AutoCrawlerPage,
})

interface ExtractionStrategy {
    target_api_url_pattern: string;
    sql_schema: string;
    transform_code: string;
    description?: string;
    target_keys?: string[];
}

interface CrawlerTaskStatus {
    id: string;
    status: "pending" | "processing" | "paused" | "completed" | "failed";
    current_phase?: "scout" | "architect" | "review" | "harvester" | "refinery" | "completed" | "failed";
    pipeline_state?: string | any;
    items_harvested?: number;
    result_sql_content?: string;
}

function AutoCrawlerPage() {
    const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
    const [logs, setLogs] = useState<string[]>([])
    const terminalRef = useRef<HTMLDivElement>(null)

    // Config State
    const [url, setUrl] = useState("https://books.toscrape.com/")
    const [tableName, setTableName] = useState("products")
    const [reviewMode, setReviewMode] = useState(true)

    // Review State
    const [isReviewOpen, setIsReviewOpen] = useState(false)
    const [strategyReview, setStrategyReview] = useState<ExtractionStrategy | null>(null)

    // Polling query
    const { data: taskStatus, refetch: refetchStatus } = useQuery<CrawlerTaskStatus>({
        queryKey: ["crawler-auto", currentTaskId],
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

    // Watch status for Phase updates and Logs
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

            // Check for Paused/Review state
            if (taskStatus.status === "paused" && taskStatus.current_phase === "review") {
                if (!isReviewOpen && state && state.strategy) {
                    setStrategyReview(state.strategy)
                    setIsReviewOpen(true)
                }
            }
        }
    }, [taskStatus])

    const startMutation = useMutation({
        mutationFn: CrawlerService.startCrawl,
        onSuccess: (taskId) => {
            setCurrentTaskId(taskId)
            setLogs(prev => [...prev, `[System] Task started: ${taskId}`])
            toast.success("Crawler task started")
        },
        onError: (err) => {
            toast.error("Failed to start crawler")
            console.error(err)
        }
    })

    const resumeMutation = useMutation({
        mutationFn: async (data: { taskId: string, strategy: any }) => {
            const token = typeof OpenAPI.TOKEN === 'function'
                ? await (OpenAPI.TOKEN as any)()
                : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            return fetch(`${baseUrl}/api/v1/crawl/resume`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ task_id: data.taskId, strategy: data.strategy })
            }).then(res => res.json())
        },
        onSuccess: () => {
            setIsReviewOpen(false)
            setLogs(prev => [...prev, `[System] Strategy confirmed. Resuming pipeline...`])
            toast.success("Pipeline resumed")
            refetchStatus()
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
                mode: "auto",
                review_mode: reviewMode
            }
        })
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

    // Helper to render phase step
    const renderStep = (phase: string, label: string, icon: any) => {
        const currentPhase = taskStatus?.current_phase || "pending"
        const phases = ["scout", "architect", "review", "harvester", "refinery", "completed"]

        // Handle failure state explicitly
        if (taskStatus?.status === 'failed' || taskStatus?.current_phase === 'failed') {
            // If failed, show failure for the active step
            // but we'll handle this simply by checking if we are past or at this step
        }

        const stepIndex = phases.indexOf(phase)
        let activeIndex = phases.indexOf(taskStatus?.status === "processing" ? "scout" : (currentPhase || "pending"))

        // Fix for "review" phase if reviewMode is false? No, reviewMode just skips it, backend handles logic.

        let statusColor = "text-muted-foreground"
        let statusBg = "bg-muted"

        if (activeIndex === stepIndex) {
            statusColor = "text-primary"
            statusBg = "bg-primary/20 ring-2 ring-primary"
        } else if (activeIndex > stepIndex) {
            statusColor = "text-green-600"
            statusBg = "bg-green-100"
        }

        if ((taskStatus?.status === 'failed' || taskStatus?.current_phase === 'failed') && activeIndex === stepIndex) {
            statusColor = "text-red-500"
            statusBg = "bg-red-100"
        }

        const Icon = icon

        return (
            <div className={`flex flex-col items-center gap-2 ${activeIndex === stepIndex ? 'scale-105 transition-transform' : ''}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${statusBg} ${statusColor}`}>
                    <Icon className="w-5 h-5" />
                </div>
                <span className={`text-xs font-medium ${statusColor}`}>{label}</span>
            </div>
        )
    }

    return (
        <div className="container mx-auto py-10 max-w-6xl space-y-8">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                    <Bot className="w-8 h-8 text-primary" />
                    Auto Crawler
                </h1>
                <p className="text-muted-foreground">
                    基于 DeepSeek AI 的自主侦察-采集-提炼流水线。
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
                                <Label htmlFor="url" className="flex items-center gap-2">
                                    <Activity className="w-3.5 h-3.5" />
                                    目标 URL
                                </Label>
                                <Input
                                    id="url"
                                    placeholder="https://books.toscrape.com/"
                                    value={url}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="table" className="flex items-center gap-2">
                                    <Database className="w-3.5 h-3.5" />
                                    表名 <span className="text-muted-foreground font-normal">（可选）</span>
                                </Label>
                                <Input
                                    id="table"
                                    placeholder="自动生成"
                                    value={tableName}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTableName(e.target.value)}
                                />
                            </div>

                            <div className="flex items-center justify-between space-x-2 border p-3 rounded-lg">
                                <div className="space-y-0.5">
                                    <Label className="text-base">运行前审查</Label>
                                    <div className="text-xs text-muted-foreground">
                                        在架构师阶段后暂停以编辑 Schema
                                    </div>
                                </div>
                                <input
                                    type="checkbox"
                                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                                    checked={reviewMode}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setReviewMode(e.target.checked)}
                                />
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
                                启动流水线
                            </Button>
                        </CardFooter>
                    </Card>
                </div>

                {/* Right Column: Visualization & Logs */}
                <div className="md:col-span-8 space-y-6">
                    {/* Progress Stepper */}
                    {currentTaskId && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-base">
                                    <Activity className="w-5 h-5" />
                                    流水线进度
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex justify-between items-center relative px-4">
                                    <div className="absolute left-0 right-0 top-5 h-0.5 bg-muted -z-10 mx-8" />
                                    {renderStep("scout", "侦察", Eye)}
                                    {renderStep("architect", "架构", Bot)}
                                    {reviewMode && renderStep("review", "审查", Settings2)}
                                    {renderStep("harvester", "收割", Activity)}
                                    {renderStep("refinery", "提炼", Database)}
                                    {renderStep("completed", "完成", PlayCircle)}
                                </div>
                            </CardContent>
                        </Card>
                    )}

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
                                {taskStatus?.current_phase && (
                                    <div className={taskStatus.current_phase === 'failed' ? "text-red-500 font-bold" : "text-green-400"}>
                                        {`> 系统当前阶段: ${taskStatus.current_phase.toUpperCase()}...`}
                                    </div>
                                )}
                                {taskStatus?.items_harvested !== undefined && (
                                    <div className="text-blue-400 font-bold">
                                        {`> 已捕获数据条数: ${taskStatus.items_harvested}`}
                                    </div>
                                )}
                                {taskStatus?.status === 'failed' && (
                                    <div className="text-red-400 mt-2">
                                        {`> 错误: 流水线执行失败。请查看后端日志以获取详细信息。`}
                                    </div>
                                )}
                                {!currentTaskId && (
                                    <div className="text-slate-600 italic">等待流水线启动...</div>
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

            {/* Review Dialog logic same as before... */}
            <Dialog open={isReviewOpen} onOpenChange={setIsReviewOpen}>
                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>运行前策略审查</DialogTitle>
                        <DialogDescription>
                            AI 架构师已分析目标并提出以下提取策略。请检查转换代码。
                        </DialogDescription>
                    </DialogHeader>

                    {strategyReview && (
                        <div className="space-y-6 py-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>目标 API 模式</Label>
                                    <Input
                                        value={strategyReview.target_api_url_pattern || ""}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStrategyReview({ ...strategyReview, target_api_url_pattern: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>表名 (Schema 推断)</Label>
                                    <div className="text-sm font-mono p-2 bg-muted rounded truncate">
                                        {(strategyReview.sql_schema || "").split('(')[0] || "Unknown"}
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>Python 清洗逻辑 (重要: 将在后端执行)</Label>
                                <div className="relative">
                                    <textarea
                                        className="flex min-h-[300px] w-full rounded-md border border-input bg-slate-950 text-green-400 px-4 py-3 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 leading-relaxed"
                                        value={strategyReview.transform_code || ""}
                                        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setStrategyReview({ ...strategyReview, transform_code: e.target.value })}
                                        spellCheck={false}
                                    />
                                    <div className="absolute top-2 right-2 flex items-center gap-1 text-[10px] text-slate-500 bg-slate-900 px-2 py-1 rounded border border-slate-800">
                                        <Code2 className="w-3 h-3" />
                                        PYTHON
                                    </div>
                                </div>
                            </div>

                            <Tabs defaultValue="schema" className="w-full">
                                <TabsList className="grid w-full grid-cols-2">
                                    <TabsTrigger value="schema">SQL Schema</TabsTrigger>
                                    <TabsTrigger value="description">策略描述</TabsTrigger>
                                </TabsList>

                                <TabsContent value="schema" className="space-y-2 mt-4">
                                    <textarea
                                        className="flex w-full rounded-md border border-input bg-background px-3 py-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring font-mono text-sm h-[200px]"
                                        value={strategyReview.sql_schema || ""}
                                        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setStrategyReview({ ...strategyReview, sql_schema: e.target.value })}
                                    />
                                </TabsContent>
                                <TabsContent value="description" className="space-y-2 mt-4">
                                    <textarea
                                        className="flex w-full rounded-md border border-input bg-background px-3 py-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-sm h-[200px]"
                                        value={strategyReview.description || ""}
                                        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setStrategyReview({ ...strategyReview, description: e.target.value })}
                                    />
                                </TabsContent>
                            </Tabs>
                        </div>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsReviewOpen(false)}>取消</Button>
                        <Button onClick={() => currentTaskId && strategyReview && resumeMutation.mutate({ taskId: currentTaskId, strategy: strategyReview })}>
                            {resumeMutation.isPending ? <Loader2 className="animate-spin mr-2" /> : <Play className="mr-2 h-4 w-4" />}
                            确认并继续
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

export default AutoCrawlerPage
