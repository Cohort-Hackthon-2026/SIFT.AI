import clsx from "clsx";

function Button({
    children,
    variant = "primary",
    className = "",
    disabled = false,
    ...props
}) {
    const variants = {
        primary:
            "bg-primary text-textInverse hover:bg-primaryHover",

        secondary:
            "bg-surface border border-border text-text hover:bg-background",

        ghost:
            "bg-transparent text-text hover:bg-background",
    };

    return (
        <button
            disabled={disabled}
            className={clsx(
                "inline-flex items-center justify-center rounded-xl px-5 py-2.5 text-sm font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50",
                variants[variant],
                className
            )}
            {...props}
        >
            {children}
        </button>
    );
}

export default Button;