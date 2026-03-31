import {
  api,
  createQuery,
  createReleaseSource,
  deleteReleaseSource,
  deleteQuery,
  getLatestReport,
  getQueries,
  getReleaseSources,
  getReportById,
  getReports,
  runArticlesPipeline,
  runReleasesPipeline,
  submitArticleFeedback,
  updateReleaseSource,
  updateQuery,
} from '@/services/api';


describe('api service', () => {
  it('uses localhost:8000 with normalized /api as fallback base URL', () => {
    expect(api.defaults.baseURL).toBe('http://localhost:8000/api');
  });

  it('calls getQueries endpoint', async () => {
    const spy = vi.spyOn(api, 'get').mockResolvedValue({ data: [] });

    await getQueries();

    expect(spy).toHaveBeenCalledWith('/queries');
    spy.mockRestore();
  });

  it('calls create/update/delete query endpoints', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { id: 1 } });
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: { id: 1 } });
    const deleteSpy = vi.spyOn(api, 'delete').mockResolvedValue({});

    await createQuery({ search_term: 'term', stream_type: 'legislative', is_active: true });
    await updateQuery(1, { search_term: 'updated' });
    await deleteQuery(1);

    expect(postSpy).toHaveBeenCalledWith('/queries', {
      search_term: 'term',
      stream_type: 'legislative',
      is_active: true,
    });
    expect(putSpy).toHaveBeenCalledWith('/queries/1', { search_term: 'updated' });
    expect(deleteSpy).toHaveBeenCalledWith('/queries/1');

    postSpy.mockRestore();
    putSpy.mockRestore();
    deleteSpy.mockRestore();
  });

  it('calls reports endpoints', async () => {
    const spy = vi.spyOn(api, 'get').mockResolvedValue({ data: [] });

    await getReports();
    await getLatestReport();
    await getLatestReport(true);
    await getReportById(7);

    expect(spy).toHaveBeenCalledWith('/reports');
    expect(spy).toHaveBeenCalledWith('/reports/latest', { params: { show_all: false, show_all_info: false } });
    expect(spy).toHaveBeenCalledWith('/reports/latest', { params: { show_all: true, show_all_info: false } });
    expect(spy).toHaveBeenCalledWith('/reports/7', { params: { show_all: false, show_all_info: false } });
    spy.mockRestore();
  });

  it('returns null from getLatestReport on 404', async () => {
    const notFoundError = Object.assign(new Error('Not found'), {
      isAxiosError: true,
      response: { status: 404 },
    });
    const spy = vi.spyOn(api, 'get').mockRejectedValue(notFoundError);

    const result = await getLatestReport();

    expect(result).toBeNull();
    spy.mockRestore();
  });

  it('posts article feedback payload', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({
      data: { status: 'success', message: 'Thank you for the feedback' },
    });

    await submitArticleFeedback(7, 'score_too_low', 9);

    expect(postSpy).toHaveBeenCalledWith('/articles/7/feedback', {
      feedback_type: 'score_too_low',
      user_corrected_score: 9,
    });
    postSpy.mockRestore();
  });

  it('calls release source endpoints', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: [] });
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { id: 1 } });
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: { id: 1 } });
    const deleteSpy = vi.spyOn(api, 'delete').mockResolvedValue({});

    await getReleaseSources();
    await createReleaseSource({
      company_name: 'IGT',
      category: 'Slot provider',
      source_url: 'https://www.igt.com/explore-igt/news/news',
      notes: 'Test notes',
      is_active: true,
    });
    await updateReleaseSource(1, { is_active: false });
    await deleteReleaseSource(1);

    expect(getSpy).toHaveBeenCalledWith('/release-sources');
    expect(postSpy).toHaveBeenCalledWith('/release-sources', {
      company_name: 'IGT',
      category: 'Slot provider',
      source_url: 'https://www.igt.com/explore-igt/news/news',
      notes: 'Test notes',
      is_active: true,
    });
    expect(putSpy).toHaveBeenCalledWith('/release-sources/1', { is_active: false });
    expect(deleteSpy).toHaveBeenCalledWith('/release-sources/1');

    getSpy.mockRestore();
    postSpy.mockRestore();
    putSpy.mockRestore();
    deleteSpy.mockRestore();
  });

  it('calls separate pipeline run endpoints', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({
      data: { status: 'success', message: 'ok' },
    });

    await runArticlesPipeline();
    await runReleasesPipeline();

    expect(postSpy).toHaveBeenCalledWith('/reports/run/articles', {}, { timeout: 300000 });
    expect(postSpy).toHaveBeenCalledWith('/reports/run/releases', {}, { timeout: 300000 });
    postSpy.mockRestore();
  });
});
