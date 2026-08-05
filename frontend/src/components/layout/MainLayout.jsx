import { useState, useEffect } from "react";

import TopBar from "./TopBar";
import Sidebar from "./Sidebar";

function MainLayout({ children }) {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    // Close sidebar on mobile when screen size changes
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth >= 1024) {
                setSidebarOpen(false);
            }
        };

        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, []);

    return (
        <div className="flex min-h-screen flex-col bg-background text-text transition-colors">
            <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
            <div className={`flex min-h-screen flex-1 flex-col ${sidebarOpen ? "lg:pl-80" : "lg:pl-0"}`}>
                <TopBar
                    sidebarOpen={sidebarOpen}
                    onToggleSidebar={() => setSidebarOpen((value) => !value)}
                />

                <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-3 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
                    {children}
                </main>
            </div>
        </div>
    );
}

export default MainLayout;
