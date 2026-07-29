function ProgressBar({
  value = 0,
}) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-background">

      <div
        className="h-full rounded-full bg-primary transition-all duration-300"
        style={{
          width: `${value}%`,
        }}
      />

    </div>
  );
}

export default ProgressBar;