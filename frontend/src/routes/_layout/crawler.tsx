import { useQuery, useMutation } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Bot, Loader2, Play, Plus, Trash2, FileText, Database, Settings2, Activity, Eye, PlayCircle, Code2, RefreshCw, Eraser, FileDown } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { toast } from "sonner"

import { CrawlerService, OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"

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

export const Route = createFileRoute("/_layout/crawler")({
  component: CrawlerPage,
})

// 定义 Strategy 接口，确保 TypeScript 知道 transform_code 的存在
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

function CrawlerPage() {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [mode, setMode] = useState<"manual" | "auto" | "industrial">("auto")
  
  // Industrial Mode State
  const [scrollCount, setScrollCount] = useState(5)
  const [batches, setBatches] = useState<Batch[]>([])
  const [selectedBatchFiles, setSelectedBatchFiles] = useState<BatchFile[]>([])
  const [isFilesDialogOpen, setIsFilesDialogOpen] = useState(false)
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null)

  // Auto Mode State
  const [reviewMode, setReviewMode] = useState(true)
  const [isReviewOpen, setIsReviewOpen] = useState(false)
  const [strategyReview, setStrategyReview] = useState<ExtractionStrategy | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const terminalRef = useRef<HTMLDivElement>(null)
  
  // Form State
  const [url, setUrl] = useState("https://books.toscrape.com/")
  const [tableName, setTableName] = useState("products")
  const [columns, setColumns] = useState<string[]>(["title", "price", "description", "category"])
  const [newColumn, setNewColumn] = useState("")
  const [maxPages, setMaxPages] = useState(1)
  const [concurrency, setConcurrency] = useState(5)

  // Polling query
  const { data: taskStatus, refetch: refetchStatus } = useQuery<CrawlerTaskStatus>({
    queryKey: ["crawler", currentTaskId],
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
          // Only update if logs have changed to avoid infinite loop or flickering
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
        
        // 安全获取 Base URL
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

  // Industrial Mode Logic
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
    if (mode === "industrial") {
        fetchBatches();
        const interval = setInterval(fetchBatches, 5000);
        return () => clearInterval(interval);
    }
  }, [mode]);

  const startIndustrialMutation = useMutation({
    mutationFn: async () => {
        const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
        const baseUrl = OpenAPI.BASE || "";
        const res = await fetch(`${baseUrl}/api/v1/industrial/collect?url=${encodeURIComponent(url)}&scroll_count=${scrollCount}`, {
            method: 'POST',
             headers: token ? { 'Authorization': `Bearer ${token}` } : {}
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
        a.download = `industrial_batch_${batchId.slice(0,8)}.zip`;
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

  const handleStartCrawl = () => {
    if (!url) {
      toast.error("Please enter a URL")
      return
    }

    setLogs([]) // Clear logs
    startMutation.mutate({
      requestBody: {
        url,
        table_name: tableName || undefined,
        columns: mode === "manual" ? columns : undefined,
        max_pages: maxPages,
        concurrency,
        mode,
        review_mode: reviewMode
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
      const token = typeof OpenAPI.TOKEN === 'function' 
          ? await (OpenAPI.TOKEN as any)() 
          : OpenAPI.TOKEN;
          
      const headers: Record<string, string> = {}
      if (typeof token === 'string') {
        headers['Authorization'] = `Bearer ${token}`
      }

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
    
    const stepIndex = phases.indexOf(phase)
    const activeIndex = phases.indexOf(taskStatus?.status === "processing" ? "scout" : (currentPhase || "pending"))
    
    let statusColor = "text-muted-foreground"
    let statusBg = "bg-muted"
    
    if (activeIndex === stepIndex) {
        statusColor = "text-primary"
        statusBg = "bg-primary/20 ring-2 ring-primary"
    } else if (activeIndex > stepIndex) {
        statusColor = "text-green-600"
        statusBg = "bg-green-100"
    }
    
    if (taskStatus?.status === 'failed' || taskStatus?.current_phase === 'failed') {
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
        <h1 className="text-3xl font-bold tracking-tight">AI 数据嗅探器</h1>
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
                    <Tabs value={mode} onValueChange={(v: any) => setMode(v)} className="w-full">
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="auto">自主模式</TabsTrigger>
                            <TabsTrigger value="manual">手动模式</TabsTrigger>
                            <TabsTrigger value="industrial">工业收割</TabsTrigger>
                        </TabsList>
                        
                        <TabsContent value="industrial" className="mt-4 space-y-4">
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
                                <Label htmlFor="scroll-ind">滚动次数 (Scroll Count)</Label>
                                <Input 
                                    id="scroll-ind" 
                                    type="number"
                                    value={scrollCount}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setScrollCount(parseInt(e.target.value) || 1)}
                                />
                            </div>
                            
                            <div className="mt-4 border rounded-md p-2 bg-slate-50 dark:bg-slate-900">
                                <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                                    <Database className="w-4 h-4" />
                                    Raw Data Lake (Batch List)
                                </h3>
                                <div className="max-h-[200px] overflow-y-auto">
                                    <table className="w-full text-xs">
                                        <thead className="bg-muted text-muted-foreground sticky top-0">
                                            <tr>
                                                <th className="p-2 text-left">Batch ID</th>
                                                <th className="p-2 text-left">Items</th>
                                                <th className="p-2 text-left">Time</th>
                                                <th className="p-2 text-left">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y">
                                            {batches.length === 0 ? (
                                                <tr><td colSpan={5} className="p-4 text-center text-muted-foreground">No batches found</td></tr>
                                            ) : (
                                                batches.map(b => (
                                                    <tr key={b.id}>
                                                        <td className="p-2 font-mono" title={b.id}>{b.id.slice(0,8)}...</td>
                                                        <td className="p-2">
                                                            <div className="flex flex-col">
                                                                <span>{b.item_count} files</span>
                                                                <span className="text-[10px] text-muted-foreground uppercase">{b.status}</span>
                                                            </div>
                                                        </td>
                                                        <td className="p-2 text-muted-foreground">{new Date(b.created_at).toLocaleString()}</td>
                                                        <td className="p-2 flex gap-2">
                                                            <Button size="sm" variant="outline" className="h-6 text-xs px-2" onClick={() => handleViewFiles(b.id)}>
                                                                <Eye className="w-3 h-3 mr-1" />
                                                                Files
                                                            </Button>
                                                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => handleDownloadBatch(b.id)} title="Download ZIP">
                                                                <FileDown className="w-3 h-3" />
                                                            </Button>
                                                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50" onClick={() => handleDeleteBatch(b.id)} title="Delete Batch">
                                                                <Trash2 className="w-3 h-3" />
                                                            </Button>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="auto" className="mt-4 space-y-4">
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
                        </TabsContent>

                        <TabsContent value="manual" className="mt-4 space-y-4">
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
                        </TabsContent>
                    </Tabs>
                </CardContent>
                <CardFooter>
                    <Button 
                        size="lg" 
                        onClick={() => {
                            if (mode === "industrial") {
                                startIndustrialMutation.mutate();
                            } else {
                                handleStartCrawl();
                            }
                        }} 
                        disabled={startMutation.isPending || startIndustrialMutation.isPending || (taskStatus?.status === "processing")}
                        className="w-full"
                    >
                        {startMutation.isPending || startIndustrialMutation.isPending ? (
                            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        ) : (
                            <Play className="mr-2 h-5 w-5" />
                        )}
                        {mode === "auto" ? "启动流水线" : (mode === "industrial" ? "开始收割" : "开始爬取")}
                    </Button>
                </CardFooter>
            </Card>
        </div>

        {/* Right Column: Visualization & Logs */}
        <div className="md:col-span-8 space-y-6">
             {/* Progress Stepper (Auto Mode Only) */}
             {mode === "auto" && currentTaskId && (
                 <Card>
                     <CardHeader>
                         <CardTitle className="flex items-center gap-2 text-base">
                             <Activity className="w-5 h-5" />
                             流水线进度
                         </CardTitle>
                     </CardHeader>
                     <CardContent>
                         <div className="flex justify-between items-center relative px-4">
                             {/* Connecting Line */}
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

      {/* Review Dialog */}
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
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStrategyReview({...strategyReview, target_api_url_pattern: e.target.value})}
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
                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setStrategyReview({...strategyReview, transform_code: e.target.value})}
                                spellCheck={false}
                            />
                            <div className="absolute top-2 right-2 flex items-center gap-1 text-[10px] text-slate-500 bg-slate-900 px-2 py-1 rounded border border-slate-800">
                                <Code2 className="w-3 h-3" />
                                PYTHON
                            </div>
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                            * 代码必须包含 `def transform_item(item):` 函数，返回字典或 None。
                        </p>
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
                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setStrategyReview({...strategyReview, sql_schema: e.target.value})}
                            />
                        </TabsContent>
                        <TabsContent value="description" className="space-y-2 mt-4">
                            <textarea 
                                className="flex w-full rounded-md border border-input bg-background px-3 py-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-sm h-[200px]"
                                value={strategyReview.description || ""}
                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setStrategyReview({...strategyReview, description: e.target.value})}
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

        {/* Industrial Files Dialog */}
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
                                        <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                                            file.content_type.includes('json') ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'
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