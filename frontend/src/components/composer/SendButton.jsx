import { ArrowUp } from "lucide-react";

function SendButton({ onClick, disabled = false }) {
    return (
        <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-xl bg-primary text-textInverse transition-all hover:bg-primaryHover disabled:cursor-not-allowed disabled:opacity-50"
        >
            <ArrowUp size={20} />
        </button>
    );
}

export default SendButton;