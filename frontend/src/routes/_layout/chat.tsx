import { useQuery, useQueryClient, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { MessageSquare, Plus, Send, Trash2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { toast } from "sonner"

import { type ChatCreate, ChatService } from "@/client"
import { CyberBackground } from "@/components/Common/CyberBackground"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export const Route = createFileRoute("/_layout/chat")({
  component: Chat,
})

function Chat() {
  const queryClient = useQueryClient()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [currentStreamText, setCurrentStreamText] = useState("")
  const [tempUserMessage, setTempUserMessage] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)

  // 1. Fetch Sessions
  const { data: sessions } = useSuspenseQuery({
    queryKey: ["sessions"],
    queryFn: () => ChatService.readSessions({ skip: 0, limit: 100 }),
  })

  // 2. Select first session by default if none selected
  useEffect(() => {
    if (!selectedSessionId && sessions?.data?.length > 0) {
      setSelectedSessionId(sessions.data[0].id)
    }
  }, [sessions, selectedSessionId])

  // 3. Fetch Chats (History) - Depends on selectedSessionId
  const { data: chats } = useQuery({
    queryKey: ["chats", selectedSessionId],
    queryFn: () => ChatService.readChats({ sessionId: selectedSessionId!, skip: 0, limit: 100 }),
    enabled: !!selectedSessionId,
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<ChatCreate>()

  const handleCreateSession = async () => {
    try {
      const newSession = await ChatService.createSession()
      await queryClient.invalidateQueries({ queryKey: ["sessions"] })
      setSelectedSessionId(newSession.id)
      setTempUserMessage(null)
      setCurrentStreamText("")
      toast.success("New chat created")
    } catch (error) {
      toast.error("Failed to create chat")
    }
  }

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (!confirm("Are you sure you want to delete this chat?")) return

    try {
      await ChatService.deleteSession({ sessionId })
      await queryClient.invalidateQueries({ queryKey: ["sessions"] })
      
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null)
        setTempUserMessage(null)
        setCurrentStreamText("")
      }
      toast.success("Chat deleted")
    } catch (error) {
      toast.error("Failed to delete chat")
    }
  }

  const onSubmit: SubmitHandler<ChatCreate> = async (data) => {
    if (!selectedSessionId) {
      toast.error("Please select or create a chat session")
      return
    }

    // 1. UI updates immediately
    setTempUserMessage(data.content)
    setIsStreaming(true)
    setCurrentStreamText("")
    reset()

    try {
      const token = localStorage.getItem("access_token")
      const baseUrl = import.meta.env.VITE_API_URL || ""
      const url = `${baseUrl}/api/v1/chat/`
      
      const payload = { ...data, session_id: selectedSessionId }

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })

      if (!response.body) throw new Error("No response body")

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        setCurrentStreamText((prev) => prev + chunk)
      }

      // Stream finished
      await queryClient.invalidateQueries({ queryKey: ["chats", selectedSessionId] })
      await queryClient.invalidateQueries({ queryKey: ["sessions"] }) // Update session list (e.g. timestamp/title)
      
      // Clear local state after data is refreshed
      setTempUserMessage(null)
      setCurrentStreamText("")
      setIsStreaming(false)
    } catch (error) {
      console.error("Streaming error:", error)
      toast.error("Failed to send message")
      setIsStreaming(false)
      setTempUserMessage(null)
    }
  }

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chats?.data, currentStreamText, tempUserMessage])

  return (
    <div className="relative flex h-[calc(100vh-14rem)] overflow-hidden rounded-2xl shadow-2xl border border-white/10">
      {/* Layer 1: Background Video + Overlay */}
      <div className="absolute inset-0 z-0">
        <CyberBackground />
        <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]" />
      </div>

      {/* Sidebar */}
      <div className="relative z-10 w-64 border-r border-white/10 bg-black/20 backdrop-blur-md p-4 flex flex-col gap-4">
        {/* Sidebar Header */}
        <div className="flex flex-col items-start mt-4">
          <Button 
            onClick={handleCreateSession} 
            className="w-full justify-start border-white/20 hover:bg-white/10 text-white" 
            variant="outline"
          >
            <Plus className="mr-2 h-4 w-4" />
            New Chat
          </Button>
        </div>
        
        <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
          {sessions?.data?.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center w-full p-2 rounded-md text-sm transition-all hover:bg-white/10 cursor-pointer ${
                selectedSessionId === session.id 
                  ? "bg-white/20 text-white shadow-lg border border-white/10" 
                  : "text-white/70"
              }`}
              onClick={() => setSelectedSessionId(session.id)}
            >
              <MessageSquare className="mr-2 h-4 w-4 opacity-70 shrink-0" />
              <span className="truncate flex-1 text-left">{session.title}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/20"
                onClick={(e) => handleDeleteSession(e, session.id)}
              >
                <Trash2 className="h-3 w-3 text-red-400" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="relative z-10 flex-1 flex flex-col p-4 h-full">
        <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-transparent custom-scrollbar mb-4">
          {!selectedSessionId && (
            <div className="flex h-full items-center justify-center text-white/50 text-lg font-light italic">
              Select or create a chat to start the journey
            </div>
          )}

          {selectedSessionId && chats?.data?.length === 0 && !tempUserMessage && (
            <div className="flex h-full items-center justify-center text-white/50 text-lg font-light italic">
              The void is waiting. Speak your mind.
            </div>
          )}
          
          {/* Render historical messages */}
          {chats?.data?.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2 duration-300`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-5 py-3 shadow-xl backdrop-blur-sm ${
                  msg.role === "user"
                    ? "bg-blue-600/80 text-white rounded-tr-sm border border-blue-400/30"
                    : "bg-white/10 text-white border border-white/20 rounded-tl-sm"
                }`}
              >
                <p className="whitespace-pre-wrap break-words leading-relaxed text-[15px]">{msg.content}</p>
              </div>
            </div>
          ))}

          {/* Render optimistic user message */}
          {tempUserMessage && (
            <div className="flex justify-end animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-xl bg-blue-600/80 text-white rounded-tr-sm border border-blue-400/30 backdrop-blur-sm">
                <p className="whitespace-pre-wrap break-words leading-relaxed text-[15px]">{tempUserMessage}</p>
              </div>
            </div>
          )}

          {/* Render streaming AI message */}
          {(isStreaming || currentStreamText) && (
            <div className="flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-xl bg-white/10 text-white border border-white/20 rounded-tl-sm backdrop-blur-sm">
                <p className="whitespace-pre-wrap break-words leading-relaxed text-[15px]">{currentStreamText}</p>
                <span className="text-[10px] text-white/40 mt-2 block animate-pulse uppercase tracking-widest font-bold">
                  Synthesizing Response...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-white/10 pt-4 bg-black/20 -mx-4 -mb-4 p-4 backdrop-blur-md">
          <form onSubmit={handleSubmit(onSubmit)} className="flex gap-2 max-w-4xl mx-auto w-full">
            <Input
              {...register("content", { required: true })}
              placeholder={selectedSessionId ? "Message the void..." : "Select a session"}
              autoComplete="off"
              className="flex-1 bg-white/5 border-white/10 text-white placeholder:text-white/30 focus-visible:ring-blue-500/50 h-12 rounded-xl"
              disabled={isSubmitting || isStreaming || !selectedSessionId}
            />
            <Button 
              type="submit" 
              disabled={isSubmitting || isStreaming || !selectedSessionId}
              className="h-12 w-12 rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/20"
            >
              <Send className="h-5 w-5" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
