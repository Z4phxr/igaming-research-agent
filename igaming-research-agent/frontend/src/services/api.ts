import axios from 'axios';
import type {
  CreateQueryDto,
  CreateReleaseSourceDto,
  FeedbackType,
  Query,
  ReleaseSource,
  Report,
  UpdateQueryDto,
  UpdateReleaseSourceDto,
} from '@/types';

function normalizeApiBaseUrl(rawBaseUrl: string): string {
  const trimmed = rawBaseUrl.replace(/\/+$/, '');
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
}

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export const api = axios.create({
  // TODO: Keep environment URLs normalized to avoid /api/api path duplication.
  baseURL: normalizeApiBaseUrl(configuredBaseUrl),
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data as
      | { detail?: string | { message?: string }; message?: string }
      | string
      | undefined;

    if (typeof responseData === 'string' && responseData.trim()) {
      if (responseData.includes('504 Gateway Time-out') || responseData.includes('<html')) {
        return 'Pipeline request timed out at the gateway. It may still be running; check reports in 1-2 minutes.';
      }
      return responseData;
    }

    if (responseData && typeof responseData === 'object') {
      if (typeof responseData.message === 'string' && responseData.message.trim()) {
        return responseData.message;
      }
      if (typeof responseData.detail === 'string' && responseData.detail.trim()) {
        return responseData.detail;
      }
      if (
        typeof responseData.detail === 'object' &&
        responseData.detail &&
        typeof responseData.detail.message === 'string' &&
        responseData.detail.message.trim()
      ) {
        return responseData.detail.message;
      }
    }
  }

  return fallback;
}

export async function getReports(): Promise<Report[]> {
  try {
    const { data } = await api.get<Report[]>('/reports');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch reports.'));
  }
}

export async function getLatestReport(showAll: boolean = false): Promise<Report | null> {
  try {
    const { data } = await api.get<Report>('/reports/latest', {
      params: { show_all: showAll },
    });
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw new Error(getApiErrorMessage(error, 'Failed to fetch latest report.'));
  }
}

export async function getReportById(id: number): Promise<Report> {
  try {
    const { data } = await api.get<Report>(`/reports/${id}`);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch report details.'));
  }
}

export async function getQueries(): Promise<Query[]> {
  try {
    const { data } = await api.get<Query[]>('/queries');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch queries.'));
  }
}

export async function createQuery(data: CreateQueryDto): Promise<Query> {
  try {
    const { data: created } = await api.post<Query>('/queries', data);
    return created;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to create query.'));
  }
}

export async function updateQuery(id: number, data: UpdateQueryDto): Promise<Query> {
  try {
    const { data: updated } = await api.put<Query>(`/queries/${id}`, data);
    return updated;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to update query.'));
  }
}

export async function deleteQuery(id: number): Promise<void> {
  try {
    await api.delete(`/queries/${id}`);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to delete query.'));
  }
}

export async function getReleaseSources(): Promise<ReleaseSource[]> {
  try {
    const { data } = await api.get<ReleaseSource[]>('/release-sources');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch release sources.'));
  }
}

export async function createReleaseSource(data: CreateReleaseSourceDto): Promise<ReleaseSource> {
  try {
    const { data: created } = await api.post<ReleaseSource>('/release-sources', data);
    return created;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to create release source.'));
  }
}

export async function updateReleaseSource(id: number, data: UpdateReleaseSourceDto): Promise<ReleaseSource> {
  try {
    const { data: updated } = await api.put<ReleaseSource>(`/release-sources/${id}`, data);
    return updated;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to update release source.'));
  }
}

export async function deleteReleaseSource(id: number): Promise<void> {
  try {
    await api.delete(`/release-sources/${id}`);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to delete release source.'));
  }
}

export async function submitArticleFeedback(
  articleId: number,
  feedbackType: FeedbackType,
  correctedScore?: number,
): Promise<{ status: string; message: string }> {
  try {
    const payload = {
      feedback_type: feedbackType,
      user_corrected_score: correctedScore,
    };
    const { data } = await api.post<{ status: string; message: string }>(`/articles/${articleId}/feedback`, payload);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to submit article feedback.'));
  }
}

export async function runPipeline(): Promise<{ status: string; message: string; articles_found?: number }> {
  try {
    const { data } = await api.post<{ status: string; message: string; articles_found?: number }>(
      '/reports/run',
      {},
      { timeout: 300000 },
    );
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && !error.response) {
      try {
        // Fallback to same-origin proxy path for deployments where frontend routes /api to backend.
        const { data } = await axios.post<{ status: string; message: string; articles_found?: number }>(
          '/api/reports/run',
          {},
          { timeout: 300000 },
        );
        return data;
      } catch (fallbackError) {
        throw new Error(getApiErrorMessage(fallbackError, 'Failed to run pipeline.'));
      }
    }
    throw new Error(getApiErrorMessage(error, 'Failed to run pipeline.'));
  }
}

export async function runArticlesPipeline(): Promise<{ status: string; message: string; articles_found?: number }> {
  try {
    const { data } = await api.post<{ status: string; message: string; articles_found?: number }>(
      '/reports/run/articles',
      {},
      { timeout: 300000 },
    );
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && !error.response) {
      try {
        const { data } = await axios.post<{ status: string; message: string; articles_found?: number }>(
          '/api/reports/run/articles',
          {},
          { timeout: 300000 },
        );
        return data;
      } catch (fallbackError) {
        throw new Error(getApiErrorMessage(fallbackError, 'Failed to run articles pipeline.'));
      }
    }
    throw new Error(getApiErrorMessage(error, 'Failed to run articles pipeline.'));
  }
}

export async function runReleasesPipeline(): Promise<{ status: string; message: string; releases_found?: number }> {
  try {
    const { data } = await api.post<{ status: string; message: string; releases_found?: number }>(
      '/reports/run/releases',
      {},
      { timeout: 300000 },
    );
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && !error.response) {
      try {
        const { data } = await axios.post<{ status: string; message: string; releases_found?: number }>(
          '/api/reports/run/releases',
          {},
          { timeout: 300000 },
        );
        return data;
      } catch (fallbackError) {
        throw new Error(getApiErrorMessage(fallbackError, 'Failed to run releases pipeline.'));
      }
    }
    throw new Error(getApiErrorMessage(error, 'Failed to run releases pipeline.'));
  }
}
