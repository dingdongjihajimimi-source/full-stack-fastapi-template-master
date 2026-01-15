import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Loader2, Eraser, Database, FileDown, Sparkles, CheckCircle2, Upload, FileUp, Zap, AlertTriangle } from "lucide-react"
import { useState, useRef } from "react"
import { toast } from "sonner"

import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export const Route = createFileRoute("/_layout/crawler/cleaning")({
    component: DataCleaningPage,
})

interface Batch {
    id: string;
    created_at: string;
    item_count: number;
    url: string;
    status: string;
}

interface BatchFile {
    name: string;
    size: number;
    content_type: string;
}

interface CleaningStats {
    original_size: number;
    cleaned_size: number;
    reduction_bytes: number;
    reduction_percent: number;
}

interface DeepCleanResult {
    mode: 'ai_extraction' | 'fallback';
    stats: CleaningStats;
    extracted_data?: any;
    ai_error?: string;
    temp_id: string;
    tokens_used?: { prompt_tokens?: number; completion_tokens?: number; };
}

function DataCleaningPage() {
    const [selectedBatchId, setSelectedBatchId] = useState<string>("")
    const [selectedFileName, setSelectedFileName] = useState<string>("")
    const [cleaningStats, setCleaningStats] = useState<CleaningStats | null>(null)
    const [cleanedFileName, setCleanedFileName] = useState<string>("")
    const [tempDownloadId, setTempDownloadId] = useState<string>("")

    // File Upload State
    const [uploadCleanStats, setUploadCleanStats] = useState<CleaningStats | null>(null)
    const [uploadedFileName, setUploadedFileName] = useState<string>("")
    const fileInputRef = useRef<HTMLInputElement>(null)
    const deepFileInputRef = useRef<HTMLInputElement>(null)

    // Deep Clean State
    const [deepCleanResult, setDeepCleanResult] = useState<DeepCleanResult | null>(null)
    const [deepTempId, setDeepTempId] = useState<string>("")

    // Fetch batches
    const { data: batches = [] } = useQuery({
        queryKey: ['batches'],
        queryFn: async () => {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const res = await fetch(`${baseUrl}/api/v1/industrial/batches`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (!res.ok) throw new Error('Failed to fetch batches');
            return res.json() as Promise<Batch[]>;
        },
        refetchInterval: 5000,
    })

    // Fetch files for selected batch
    const { data: batchFiles = [] } = useQuery({
        queryKey: ['batch-files', selectedBatchId],
        queryFn: async () => {
            if (!selectedBatchId) return [];
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const res = await fetch(`${baseUrl}/api/v1/industrial/batch/${selectedBatchId}/files`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (!res.ok) throw new Error('Failed to fetch files');
            return res.json() as Promise<BatchFile[]>;
        },
        enabled: !!selectedBatchId,
    })

    // Batch Light clean mutation
    const lightCleanMutation = useMutation({
        mutationFn: async () => {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const res = await fetch(`${baseUrl}/api/v1/industrial/batch/${selectedBatchId}/light-clean`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ file_name: selectedFileName })
            });
            if (!res.ok) throw new Error('Cleaning failed');
            return res.json();
        },
        onSuccess: (data) => {
            setCleaningStats(data.stats);
            setCleanedFileName(data.output_file);
            toast.success(`文件清洗完成！体积减少 ${data.stats.reduction_percent}%`);
        },
        onError: () => toast.error("清洗失败")
    });

    // Upload & Clean mutation
    const uploadCleanMutation = useMutation({
        mutationFn: async (file: File) => {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";

            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch(`${baseUrl}/api/v1/industrial/upload-clean`, {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Upload cleaning failed');
            }
            return res.json();
        },
        onSuccess: (data) => {
            setUploadCleanStats(data.stats);
            setTempDownloadId(data.temp_id);
            setUploadedFileName(data.original_name);
            toast.success(`上传清洗完成！体积减少 ${data.stats.reduction_percent}%`);
        },
        onError: (e) => toast.error(`清洗失败: ${e.message}`)
    });

    // Deep Clean mutation (AI extraction)
    const deepCleanMutation = useMutation({
        mutationFn: async (file: File) => {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";

            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch(`${baseUrl}/api/v1/industrial/upload-deep-clean`, {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Deep clean failed');
            }
            return res.json();
        },
        onSuccess: (data) => {
            setDeepCleanResult(data);
            setDeepTempId(data.temp_id);
            setUploadedFileName(data.original_name);
            if (data.mode === 'ai_extraction') {
                toast.success(`AI 提取成功！`);
            } else {
                toast.warning(`AI 提取失败，已回退到浅清洗`);
            }
        },
        onError: (e) => toast.error(`深度清洗失败: ${e.message}`)
    });

    const handleDeepFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            deepCleanMutation.mutate(e.target.files[0]);
        }
    };

    const handleDownloadJson = async () => {
        if (!deepTempId) return;
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const response = await fetch(`${baseUrl}/api/v1/industrial/temp-json/${deepTempId}`, {
                method: 'GET',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) throw new Error('Download failed');
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `extracted_${uploadedFileName.replace('.html', '.json')}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
            toast.success("JSON 下载完成");
        } catch (e) {
            toast.error("下载失败");
        }
    };

    const handleDownloadCleanedFile = async () => {
        if (!selectedBatchId || !cleanedFileName) return;
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            const response = await fetch(`${baseUrl}/api/v1/industrial/batch/${selectedBatchId}/file/${cleanedFileName}`, {
                method: 'GET',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) throw new Error('Download failed');
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = cleanedFileName;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
            toast.success("下载完成");
        } catch (e) {
            toast.error("下载失败");
        }
    }

    const handleDownloadTempFile = async () => {
        if (!tempDownloadId) return;
        try {
            const token = typeof OpenAPI.TOKEN === 'function' ? await (OpenAPI.TOKEN as any)() : OpenAPI.TOKEN;
            const baseUrl = OpenAPI.BASE || "";
            // Use window.open for temp file download or similar blob method
            // Security: auth token might be tricky with window.open if cookies not set, so use fetch blob
            const response = await fetch(`${baseUrl}/api/v1/industrial/temp-file/${tempDownloadId}`, {
                method: 'GET',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) throw new Error('Download failed');
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `cleaned_${uploadedFileName}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
            toast.success("下载完成");
        } catch (e) {
            toast.error("下载失败");
        }
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            uploadCleanMutation.mutate(e.target.files[0]);
        }
    };

    const htmlFiles = batchFiles.filter(f => f.name.endsWith('.html'));

    const renderStats = (stats: CleaningStats | null, onDownload: () => void, downloadLabel: string) => {
        if (!stats) return null;
        return (
            <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="space-y-1">
                        <div className="text-muted-foreground text-xs">原始大小</div>
                        <div className="font-mono font-semibold">
                            {(stats.original_size / 1024).toFixed(1)} KB
                        </div>
                    </div>
                    <div className="space-y-1">
                        <div className="text-muted-foreground text-xs">清洗后大小</div>
                        <div className="font-mono font-semibold text-green-600">
                            {(stats.cleaned_size / 1024).toFixed(1)} KB
                        </div>
                    </div>
                    <div className="space-y-1">
                        <div className="text-muted-foreground text-xs">减少体积</div>
                        <div className="font-mono font-semibold">
                            {(stats.reduction_bytes / 1024).toFixed(1)} KB
                        </div>
                    </div>
                    <div className="space-y-1">
                        <div className="text-muted-foreground text-xs">压缩比</div>
                        <div className="font-mono font-semibold text-blue-600">
                            {stats.reduction_percent.toFixed(1)}%
                        </div>
                    </div>
                </div>

                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-md border border-green-200 dark:border-green-800">
                    <div className="text-xs text-green-700 dark:text-green-300 font-medium mb-1">
                        ✅ 清洗完成
                    </div>
                    <div className="text-xs text-muted-foreground">
                        点击下方按钮下载结果
                    </div>
                </div>

                <Button
                    className="w-full"
                    variant="outline"
                    onClick={onDownload}
                >
                    <FileDown className="mr-2 h-4 w-4" />
                    {downloadLabel}
                </Button>
            </div>
        );
    };

    return (
        <div className="container mx-auto py-10 max-w-4xl space-y-8">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                    <Eraser className="w-8 h-8 text-primary" />
                    数据清洗 (Data Cleaning)
                </h1>
                <p className="text-muted-foreground">
                    轻量级 HTML 预处理，剔除无效标签，大幅压缩文件体积。
                </p>
            </div>

            <Tabs defaultValue="upload" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="upload" className="flex items-center gap-2">
                        <Upload className="w-4 h-4" />
                        上传文件清洗 (Upload & Clean)
                    </TabsTrigger>
                    <TabsTrigger value="batch" className="flex items-center gap-2">
                        <Database className="w-4 h-4" />
                        批次清洗 (Batch Clean)
                    </TabsTrigger>
                </TabsList>

                {/* Upload Tab - Now with Light Clean + Deep Clean */}
                <TabsContent value="upload" className="space-y-4 py-4">
                    <div className="grid gap-6 md:grid-cols-2">
                        {/* Light Clean Section */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <FileUp className="w-5 h-5" />
                                    浅清洗 (Light Clean)
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="border-2 border-dashed border-muted-foreground/30 rounded-lg p-6 text-center hover:bg-muted/50 transition-colors cursor-pointer"
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        className="hidden"
                                        accept=".html,.htm"
                                        onChange={handleFileUpload}
                                    />
                                    <div className="flex flex-col items-center gap-2">
                                        {uploadCleanMutation.isPending ? (
                                            <Loader2 className="w-8 h-8 animate-spin text-primary" />
                                        ) : (
                                            <Upload className="w-8 h-8 text-muted-foreground" />
                                        )}
                                        <p className="font-medium text-sm">去除 JS/CSS/SVG</p>
                                        <p className="text-xs text-muted-foreground">返回精简 HTML</p>
                                    </div>
                                </div>
                                {uploadCleanStats && renderStats(uploadCleanStats, handleDownloadTempFile, "下载 HTML")}
                            </CardContent>
                        </Card>

                        {/* Deep Clean (AI) Section */}
                        <Card className="border-primary/30">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-primary">
                                    <Zap className="w-5 h-5" />
                                    深度清洗 (AI Extraction)
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="border-2 border-dashed border-primary/30 rounded-lg p-6 text-center hover:bg-primary/5 transition-colors cursor-pointer"
                                    onClick={() => deepFileInputRef.current?.click()}
                                >
                                    <input
                                        type="file"
                                        ref={deepFileInputRef}
                                        className="hidden"
                                        accept=".html,.htm"
                                        onChange={handleDeepFileUpload}
                                    />
                                    <div className="flex flex-col items-center gap-2">
                                        {deepCleanMutation.isPending ? (
                                            <Loader2 className="w-8 h-8 animate-spin text-primary" />
                                        ) : (
                                            <Sparkles className="w-8 h-8 text-primary" />
                                        )}
                                        <p className="font-medium text-sm">AI 智能提取</p>
                                        <p className="text-xs text-muted-foreground">返回结构化 JSON</p>
                                    </div>
                                </div>

                                {/* Deep Clean Result */}
                                {deepCleanResult && (
                                    <div className="space-y-3">
                                        {deepCleanResult.mode === 'ai_extraction' ? (
                                            <>
                                                <div className="flex items-center gap-2 text-green-600">
                                                    <CheckCircle2 className="w-4 h-4" />
                                                    <span className="text-sm font-medium">AI 提取成功</span>
                                                </div>
                                                {deepCleanResult.tokens_used && (
                                                    <p className="text-xs text-muted-foreground">
                                                        Token: {deepCleanResult.tokens_used.prompt_tokens} + {deepCleanResult.tokens_used.completion_tokens}
                                                    </p>
                                                )}
                                                <div className="bg-muted rounded-lg p-3 max-h-48 overflow-auto">
                                                    <pre className="text-xs whitespace-pre-wrap">
                                                        {JSON.stringify(deepCleanResult.extracted_data, null, 2).slice(0, 500)}
                                                        {JSON.stringify(deepCleanResult.extracted_data, null, 2).length > 500 && '...'}
                                                    </pre>
                                                </div>
                                                <Button onClick={handleDownloadJson} className="w-full">
                                                    <FileDown className="w-4 h-4 mr-2" />
                                                    下载 JSON
                                                </Button>
                                            </>
                                        ) : (
                                            <div className="flex items-center gap-2 text-yellow-600">
                                                <AlertTriangle className="w-4 h-4" />
                                                <span className="text-sm">已回退到浅清洗: {deepCleanResult.ai_error}</span>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* Batch Tab */}
                <TabsContent value="batch" className="space-y-4 py-4">
                    <div className="grid gap-6 md:grid-cols-2">
                        {/* Left: Configuration */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Database className="w-5 h-5" />
                                    选择数据库批次
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>选择批次 (Batch)</Label>
                                    <Select value={selectedBatchId} onValueChange={(v) => {
                                        setSelectedBatchId(v);
                                        setSelectedFileName("");
                                        setCleaningStats(null);
                                        setCleanedFileName("");
                                    }}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="选择一个已收割的批次" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {batches.map(b => (
                                                <SelectItem key={b.id} value={b.id}>
                                                    {b.id.slice(0, 8)} - {b.url.slice(0, 40)} ({b.item_count} items)
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {selectedBatchId && (
                                    <div className="space-y-2">
                                        <Label>选择 HTML 文件</Label>
                                        <Select value={selectedFileName} onValueChange={(v) => {
                                            setSelectedFileName(v);
                                            setCleaningStats(null);
                                            setCleanedFileName("");
                                        }}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="选择要清洗的 HTML 文件" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {htmlFiles.length === 0 ? (
                                                    <div className="p-2 text-xs text-muted-foreground">此批次无 HTML 文件</div>
                                                ) : (
                                                    htmlFiles.map(f => (
                                                        <SelectItem key={f.name} value={f.name}>
                                                            {f.name} ({(f.size / 1024).toFixed(1)} KB)
                                                        </SelectItem>
                                                    ))
                                                )}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}

                                <div className="pt-4 border-t">
                                    <Button
                                        className="w-full"
                                        size="lg"
                                        disabled={!selectedFileName || lightCleanMutation.isPending}
                                        onClick={() => lightCleanMutation.mutate()}
                                    >
                                        {lightCleanMutation.isPending ? (
                                            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                        ) : (
                                            <Sparkles className="mr-2 h-5 w-5" />
                                        )}
                                        浅清洗 (batch clean)
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Right: Results */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <CheckCircle2 className="w-5 h-5" />
                                    清洗结果
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                {cleaningStats ? (
                                    renderStats(cleaningStats, handleDownloadCleanedFile, "下载预览 (Download Preview)")
                                ) : (
                                    <div className="text-center py-12 text-muted-foreground">
                                        <Eraser className="w-12 h-12 mx-auto mb-3 opacity-20" />
                                        <p className="text-sm">请选择文件并执行清洗</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>
            </Tabs>

            {/* Info Card */}
            <Card className="bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800">
                <CardContent className="pt-6">
                    <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-blue-600" />
                        浅清洗说明 (Light Clean)
                    </h3>
                    <ul className="text-xs space-y-1 text-muted-foreground">
                        <li>• 自动剔除视觉标签 (&lt;style&gt;, &lt;svg&gt;, &lt;path&gt;)</li>
                        <li>• 移除脚本标签 (&lt;script&gt;) 及其内容</li>
                        <li>• 删除无意义属性 (class, id, style)</li>
                        <li>• 保留文本内容和结构标签 (&lt;div&gt;, &lt;table&gt;)</li>
                        <li>• 适合作为 AI 提取的预处理步骤</li>
                    </ul>
                </CardContent>
            </Card>
        </div>
    )
}

export default DataCleaningPage
