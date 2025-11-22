import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../api/client";

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30000,
  });
}

