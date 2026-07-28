export default function SkeletonCard() {
  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl overflow-hidden animate-pulse">
      <div className="h-40 bg-[#1A1A1A]" />
      <div className="p-4 space-y-3">
        <div className="h-4 bg-[#1F2937] rounded w-3/4" />
        <div className="h-3 bg-[#1F2937] rounded w-1/3" />
        <div className="flex gap-2">
          <div className="h-5 bg-[#1F2937] rounded-full w-14" />
          <div className="h-5 bg-[#1F2937] rounded-full w-14" />
          <div className="h-5 bg-[#1F2937] rounded-full w-14" />
        </div>
        <div className="h-3 bg-[#1F2937] rounded w-full" />
        <div className="h-3 bg-[#1F2937] rounded w-2/3" />
        <div className="h-2 bg-[#1F2937] rounded w-full" />
        <div className="flex justify-between pt-2">
          <div className="h-4 bg-[#1F2937] rounded w-16" />
          <div className="h-4 bg-[#1F2937] rounded w-20" />
        </div>
        <div className="flex gap-2 pt-1">
          <div className="h-8 bg-[#1F2937] rounded-lg flex-1" />
          <div className="h-8 bg-[#1F2937] rounded-lg flex-1" />
        </div>
      </div>
    </div>
  );
}
