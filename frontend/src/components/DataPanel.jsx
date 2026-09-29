import { useCallback, useState } from "react";
import { Search, RefreshCw } from "lucide-react";
import { api } from "../api";
import { useApi } from "./shared";
import { ErrorDisplay, Loading } from "./ui";

const CONFIG = {
  products: { title: "Products", description: "Products referenced by support tickets.", columns: [["sku", "SKU"], ["product_name", "Product"], ["family", "Family"], ["retail_price_inr", "Retail price"], ["warranty_months", "Warranty"]] },
  customers: { title: "Customers", description: "Customer reference records linked to support tickets.", columns: [["customer_id", "ID"], ["name", "Name"], ["city", "City"], ["state", "State"], ["care_plus", "Care Plus"]] },
  orders: { title: "Orders", description: "Orders available for ticket and customer context.", columns: [["order_id", "Order"], ["customer_id", "Customer"], ["sku", "SKU"], ["order_date", "Date"], ["order_value_inr", "Value"]] },
  tickets: { title: "Ticket Explorer", description: "Search the deduplicated ticket export by ID, customer, product, or category.", columns: [["ticket_id", "Ticket"], ["created_at", "Created"], ["customer_id", "Customer"], ["product_sku", "Product"], ["category", "Category"], ["status", "Status"]] },
  evaluation: { title: "Evaluation", description: "Quality checks and operating signals for the analytics pipeline.", columns: [["metric", "Metric"], ["value", "Value"], ["detail", "Detail"]] },
};

function displayValue(value) {
  if (value == null || value === "") return "-";
  if (typeof value === "number") return value.toLocaleString("en-IN");
  return String(value);
}

export default function DataPanel({ resource }) {
  const config = CONFIG[resource] || CONFIG.products;
  const [query, setQuery] = useState("");
  const fetchData = useCallback(() => api.getData(resource, query), [resource, query]);
  const { data, loading, error, refetch } = useApi(
    fetchData,
  );

  return (
    <div className="fade-in">
      <div className="data-page-heading">
        <div><div className="eyebrow">DATA WORKSPACE</div><h2>{config.title}</h2><p>{config.description}</p></div>
        <button className="secondary-action" onClick={refetch}><RefreshCw size={14} /> Refresh</button>
      </div>
      <div className="data-toolbar">
        <div className="search-control"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Search ${config.title.toLowerCase()}...`} /></div>
        <span className="result-count">{data?.length ?? 0} records shown</span>
      </div>
      {loading && <Loading text={`Loading ${config.title.toLowerCase()}...`} />}
      {error && <ErrorDisplay message={error} onRetry={refetch} />}
      {!loading && !error && (
        <div className="section-card data-browser-card"><div className="table-wrapper"><table className="data-table"><thead><tr>{config.columns.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead><tbody>{data?.map((row, index) => <tr key={row.ticket_id || row.order_id || row.product_id || row.customer_id || index}>{config.columns.map(([key]) => <td key={key}>{displayValue(row[key])}</td>)}</tr>)}</tbody></table>{!data?.length && <div className="empty-state">No records match this search.</div>}</div></div>
      )}
    </div>
  );
}
