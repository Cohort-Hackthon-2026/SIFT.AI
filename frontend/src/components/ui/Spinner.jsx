function Spinner({ size = 18 }) {
    return (
        <div
            className="animate-spin rounded-full border-2 border-border border-t-primary"
            style={{
                width: size,
                height: size,
            }}
        />
    );
}

export default Spinner;