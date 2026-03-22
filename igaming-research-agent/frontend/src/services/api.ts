import axios from 'axios';
import type { CreateQueryDto, FeedbackType, Query, Report, UpdateQueryDto } from '@/types';

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
      | { detail?: string | { message?: string } }
      | string
      | undefined;

    if (typeof responseData === 'string' && responseData.trim()) {
      return responseData;
    }

    if (responseData && typeof responseData === 'object') {
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
    const { data } = await api.post<{ status: string; message: string; articles_found?: number }>('/reports/run');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to run pipeline.'));
  }
}
