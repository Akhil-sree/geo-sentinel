export type ReportStatus = "PENDING" | "VERIFIED" | "REJECTED" | "USED_FOR_TRAINING";

export interface CitizenReport {
  id: string; lat: number; lng: number;
  type: string | null; severity: string | null;
  description: string | null; photo_url: string | null;
  status: ReportStatus; at: string | null;
}
