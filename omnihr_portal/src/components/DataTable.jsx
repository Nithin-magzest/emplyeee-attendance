import React, { useState, useMemo } from 'react';
import { Search, ChevronUp, ChevronDown, Inbox } from 'lucide-react';

export default function DataTable({
  columns = [],
  data = [],
  pageSize = 20,
  searchable = true,
  title,
  subtitle,
  actions,
  loading = false,
}) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [currentPage, setCurrentPage] = useState(1);

  const handleSort = (key, sortable) => {
    if (!sortable) return;
    if (sortKey === key) {
      if (sortDir === 'asc') setSortDir('desc');
      else { setSortKey(null); setSortDir('asc'); }
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const filteredData = useMemo(() => {
    if (!search) return data;
    const lowerSearch = search.toLowerCase();
    return data.filter(row => 
      columns.some(col => {
        const val = row[col.key];
        return val != null && String(val).toLowerCase().includes(lowerSearch);
      })
    );
  }, [data, search, columns]);

  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortKey, sortDir]);

  const totalPages = Math.ceil(sortedData.length / pageSize) || 1;
  
  // Reset page when search or sort changes
  useMemo(() => { setCurrentPage(1); }, [search, sortKey, sortDir]);

  const currentData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  return (
    <div className="dt-wrapper card">
      <div className="dt-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          {title && <h3 className="page-title text-lg font-bold">{title}</h3>}
          {subtitle && <p className="page-subtitle text-sm text-muted">{subtitle}</p>}
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {searchable && (
            <div className="dt-search" style={{ position: 'relative' }}>
              <Search style={{ position: 'absolute', left: '0.5rem', top: '50%', transform: 'translateY(-50%)', color: '#9CA3AF' }} size={16} />
              <input
                type="text"
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="form-input"
                style={{ paddingLeft: '2rem' }}
              />
            </div>
          )}
          {actions && <div>{actions}</div>}
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="dt-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  onClick={() => handleSort(col.key, col.sortable)}
                  style={{ cursor: col.sortable ? 'pointer' : 'default', padding: '0.75rem', textAlign: 'left', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    {col.label}
                    {col.sortable && sortKey === col.key && (
                      sortDir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={`loading-${i}`}>
                  {columns.map((_, j) => (
                    <td key={`col-${j}`} style={{ padding: '0.75rem', borderBottom: '1px solid #E5E7EB' }}>
                      <div className="skeleton" style={{ height: '16px', borderRadius: '4px' }}></div>
                    </td>
                  ))}
                </tr>
              ))
            ) : currentData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: '3rem', textAlign: 'center' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#9CA3AF' }}>
                    <Inbox size={48} style={{ marginBottom: '1rem' }} />
                    <p>No results found</p>
                  </div>
                </td>
              </tr>
            ) : (
              currentData.map((row, i) => (
                <tr key={row.id || i} style={{ borderBottom: '1px solid #E5E7EB' }}>
                  {columns.map((col, j) => (
                    <td key={`cell-${j}`} style={{ padding: '0.75rem' }}>
                      {col.render ? col.render(row[col.key], row) : row[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!loading && sortedData.length > 0 && (
        <div className="dt-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
          <div className="text-sm text-muted">
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length} entries
          </div>
          <div className="pagination" style={{ display: 'flex', gap: '0.25rem' }}>
            <button
              className="page-btn btn btn-sm btn-ghost"
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              Prev
            </button>
            {Array.from({ length: totalPages }).map((_, i) => {
              const page = i + 1;
              if (page === 1 || page === totalPages || (page >= currentPage - 1 && page <= currentPage + 1)) {
                return (
                  <button
                    key={page}
                    className={`page-btn btn btn-sm ${page === currentPage ? 'active btn-primary' : 'btn-ghost'}`}
                    onClick={() => setCurrentPage(page)}
                  >
                    {page}
                  </button>
                );
              }
              if (page === currentPage - 2 || page === currentPage + 2) {
                return <span key={page} style={{ padding: '0.25rem' }}>...</span>;
              }
              return null;
            })}
            <button
              className="page-btn btn btn-sm btn-ghost"
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
