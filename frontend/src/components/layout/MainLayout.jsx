import TopBar from "./TopBar";

function MainLayout({ children }) {
    return (
        <div className="flex min-h-screen flex-col bg-background text-text transition-colors">
            <TopBar />

            <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-6 sm:px-6 lg:px-8">
                {children}
            </main>
        </div>
    );
}

export default MainLayout;