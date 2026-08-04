import {
    ArrowRight,
    FileSearch,
    Globe2,
    ShieldCheck,
} from "lucide-react";

import Button from "../ui/Button";
import { useAuth } from "../../../store/auth";
import { useTheme } from "../../../store/theme";
import { getThemeColors } from "../../../utils/Colors";

function WelcomeView({
    onSignIn,
    onSignUp,
    onClose,
}) {
    const theme = useTheme((state) => state.theme);
    const colors = getThemeColors(theme);
    const continueAsGuest = useAuth(
        (state) => state.continueAsGuest
    );

    const handleGuest = () => {
        continueAsGuest();
        onClose?.();
    };

    return (
        <div
            className="p-8"
            style={{ color: colors.text }}
        >

            <div
                className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl shadow-lg shadow-primary/20"
                style={{
                    backgroundColor: colors.primary,
                    color: colors.textInverse,
                }}
            >

                <FileSearch size={30} />

            </div>

            <div className="mt-6 text-center">

                <h1
                    className="text-3xl font-bold"
                    style={{ color: colors.text }}
                >
                    Welcome to Sift AI
                </h1>

                <p
                    className="mt-3 leading-7"
                    style={{ color: colors.text }}
                >
                    Upload PDFs, search documents, verify
                    citations, and enhance research with AI.
                </p>

            </div>

            <div className="mt-8 space-y-3">

                <div className="flex items-center gap-3 rounded-2xl border border-border bg-background/80 p-4">

                    <ShieldCheck
                        size={20}
                        style={{ color: colors.primary }}
                    />

                    <span
                        className="text-sm"
                        style={{ color: colors.text }}
                    >
                        Strict Mode answers only from your
                        uploaded documents.
                    </span>

                </div>

                <div className="flex items-center gap-3 rounded-2xl border border-border bg-background/80 p-4">

                    <Globe2
                        size={20}
                        style={{ color: colors.primary }}
                    />

                    <span
                        className="text-sm"
                        style={{ color: colors.text }}
                    >
                        Enhanced Mode combines documents
                        with trusted web results.
                    </span>

                </div>

            </div>

            <div className="mt-8 space-y-3">

                <Button
                    className="w-full"
                    onClick={onSignUp}
                    style={{
                        backgroundColor: colors.primary,
                        color: colors.textInverse,
                    }}
                >
                    Create Account
                </Button>

                <Button
                    variant="secondary"
                    className="w-full"
                    onClick={onSignIn}
                    style={{
                        borderColor: colors.primary,
                        color: colors.primary,
                    }}
                >
                    Sign In
                </Button>

            </div>

            <button
                onClick={handleGuest}
                className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl border bg-surface px-4 py-3 text-sm font-medium transition hover:bg-background"
                style={{
                    borderColor: colors.primary,
                    color: colors.primary,
                }}
            >
                Continue as Guest

                <ArrowRight size={16} />
            </button>

        </div>
    );
}

export default WelcomeView;
