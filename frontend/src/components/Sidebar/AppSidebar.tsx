import { Home, Package, MessageCircle, Sparkles, MousePointer, Factory, Eraser, Settings } from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: Package, title: "Items", path: "/items" },
  { icon: MessageCircle, title: "Chat", path: "/chat" },
  { icon: Sparkles, title: "Auto Crawler", path: "/crawler/auto" },
  { icon: MousePointer, title: "Manual Scraper", path: "/crawler/manual" },
  { icon: Factory, title: "Industrial Harvest", path: "/crawler/industrial" },
  { icon: Eraser, title: "Data Cleaning", path: "/crawler/cleaning" },
  { icon: Settings, title: "Admin", path: "/admin" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items = baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
