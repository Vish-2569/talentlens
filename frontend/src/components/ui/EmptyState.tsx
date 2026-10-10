interface Props {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-hairline bg-paper px-6 py-12 text-center">
      <p className="font-serif text-base text-muted">{title}</p>
      {description && (
        <p className="mt-1 text-xs font-sans text-muted">{description}</p>
      )}
    </div>
  );
}
