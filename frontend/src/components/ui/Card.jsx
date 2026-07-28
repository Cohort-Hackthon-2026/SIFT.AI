import clsx from "clsx";

function Card({
    children,
    className = "",
}) {
    return (
        <div
            className={clsx(
                "rounded-2xl border border-border bg-surface",
                className
            )}
        >
            {children}
        </div>
    );
}

export default Card;