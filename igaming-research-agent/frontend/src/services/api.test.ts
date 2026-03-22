import {
  api,
  createQuery,
  deleteQuery,
  getQueries,
  getReportById,
  getReports,
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
    await getReportById(7);

    expect(spy).toHaveBeenCalledWith('/reports');
    expect(spy).toHaveBeenCalledWith('/reports/7');
    spy.mockRestore();
  });
});
