import { ArrowUp } from "lucide-react";

function SendButton() {
    return (
        <button className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-textInverse transition-all hover:bg-primaryHover disabled:opacity-50 cursor-pointer">

            <ArrowUp size={20} />

        </button>
    );
}

export default SendButton;