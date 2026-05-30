import { prisma } from "./prisma";

export async function getPredictions(filters: {
  nicheId?: number;
  status?: string;
  limit?: number;
}) {
  return prisma.prediction.findMany({
    where: {
      ...(filters.nicheId ? { matchedNicheId: filters.nicheId } : {}),
      ...(filters.status ? { status: filters.status } : {}),
    },
    include: { niche: true },
    orderBy: { breakoutScore: "desc" },
    take: filters.limit ?? 100,
  });
}

export async function getPredictionById(id: number) {
  return prisma.prediction.findUnique({
    where: { id },
    include: { niche: true },
  });
}

export async function getNiches() {
  return prisma.niche.findMany({
    select: { id: true, name: true },
    orderBy: { name: "asc" },
  });
}
