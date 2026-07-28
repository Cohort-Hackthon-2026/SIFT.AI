import clsx from "clsx";

function IconButton({
    icon: Icon,
    className = "",
    ...props
}) {
    return (
        <button
            className={clsx(
                "flex h-11 w-11 items-center justify-center rounded-xl bg-surface border border-border text-text transition-all hover:bg-background",
                className
            )}
            {...props}
        >
            <Icon size={20} />
        </button>
    );
}

export default IconButton;