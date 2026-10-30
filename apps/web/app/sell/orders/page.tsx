"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  ExternalLink,
  MapPin,
  Mic,
  Package,
  Phone,
  QrCode,
  RotateCcw,
  Search,
  Truck,
  X,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { PageHeader } from "@/components/seller/PageHeader";
import { UnderlineTabs, type TabItem } from "@/components/seller/Tabs";
import { VoiceField } from "@/components/seller/VoiceField";
import { api } from "@/lib/api";
import { cx, inr } from "@/lib/format";

interface ArtisanOrderItem {
  id: string;
  orderNumber: string;
  status: "to_pack" | "shipped" | "delivered" | "returns";
  title: string;
  thumbnailUrl: string;
  priceInr: number;
  karuId: string;
  orderedOn: string;
  buyerName: string;
  buyerCity: string;
  shipAddress?: string;
  courier?: string;
  trackingNo?: string;
  returnReason?: string;
}

const MOCK_ORDERS: ArtisanOrderItem[] = [
  {
    id: "ord-1",
    orderNumber: "OD-2026-8812",
    status: "to_pack",
    title: "Bhagalpuri Handwoven Tussar Silk Saree",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=300&q=80",
    priceInr: 2800,
    karuId: "KA-SLK-481-01",
    orderedOn: "30 Oct 2026, 09:15 AM",
    buyerName: "Ananya",
    buyerCity: "Bengaluru",
    shipAddress: "Flat 402, Green Glen Layout, Bellandur, Bengaluru 560103",
  },
  {
    id: "ord-2",
    orderNumber: "OD-2026-8809",
    status: "to_pack",
    title: "Jaipur Blue Pottery Floral Fruit Bowl",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=300&q=80",
    priceInr: 1250,
    karuId: "KA-POT-112-04",
    orderedOn: "30 Oct 2026, 08:30 AM",
    buyerName: "Rohan",
    buyerCity: "Mumbai",
    shipAddress: "B-12, JVPD Scheme, Juhu, Mumbai 400049",
  },
  {
    id: "ord-3",
    orderNumber: "OD-2026-8790",
    status: "shipped",
    title: "Kashmiri Hand-Embroidered Sozni Pashmina",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1607344645866-009c320c5ab8?auto=format&fit=crop&w=300&q=80",
    priceInr: 9500,
    karuId: "KA-SHW-204-02",
    orderedOn: "28 Oct 2026, 02:20 PM",
    buyerName: "Priya",
    buyerCity: "New Delhi",
    shipAddress: "C-45, Vasant Vihar, New Delhi 110057",
    courier: "Delhivery Express",
    trackingNo: "DEL-77891230",
  },
  {
    id: "ord-4",
    orderNumber: "OD-2026-8711",
    status: "delivered",
    title: "Bidriware Silver Inlay Keepsake Box",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=300&q=80",
    priceInr: 3600,
    karuId: "KA-BDR-098-01",
    orderedOn: "24 Oct 2026, 11:45 AM",
    buyerName: "Vikram",
    buyerCity: "Hyderabad",
    shipAddress: "Road No. 36, Jubilee Hills, Hyderabad 500033",
    courier: "BlueDart",
    trackingNo: "BD-99120485",
  },
  {
    id: "ord-5",
    orderNumber: "OD-2026-8699",
    status: "returns",
    title: "Kutch Rogan Painted Silk Wall Hanging",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1582562124811-c09040d0a901?auto=format&fit=crop&w=300&q=80",
    priceInr: 4200,
    karuId: "KA-RGN-552-03",
    orderedOn: "20 Oct 2026, 03:10 PM",
    buyerName: "Sunita",
    buyerCity: "Pune",
    returnReason: "Size smaller than expected frame dimensions",
  },
];

export default function SellerOrdersPage() {
  return (
    <Suspense>
      <OrdersContent />
    </Suspense>
  );
}

function OrdersContent() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") === "returns" ? "returns" : "to_pack";
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const [selectedOrderForDrawer, setSelectedOrderForDrawer] = useState<ArtisanOrderItem | null>(null);
  const [shippingModalOrder, setShippingModalOrder] = useState<ArtisanOrderItem | null>(null);
  const [courierName, setCourierName] = useState("Delhivery");
  const [trackingNumber, setTrackingNumber] = useState("");

  const tabs: TabItem[] = [
    { id: "to_pack", label: "To pack", count: 2 },
    { id: "shipped", label: "Shipped", count: 1 },
    { id: "delivered", label: "Delivered", count: 1 },
    { id: "returns", label: "Returns", count: 1 },
  ];

  const currentOrders = MOCK_ORDERS.filter((o) => o.status === activeTab);

  const handleMarkShipped = () => {
    if (shippingModalOrder) {
      shippingModalOrder.status = "shipped";
      shippingModalOrder.courier = courierName;
      shippingModalOrder.trackingNo = trackingNumber || `TRK-${Date.now().toString().slice(-6)}`;
      setShippingModalOrder(null);
      setCourierName("Delhivery");
      setTrackingNumber("");
    }
  };

  return (
    <div className="flex flex-col min-w-0">
      <PageHeader
        title="Orders & Shipments"
        howToText="How to pack & dispatch orders"
      />

      <div className="max-w-[1240px] w-full mx-auto px-4 sm:px-6 py-5 flex flex-col gap-4">
        {/* Main Card with Tabs & Data Table */}
        <div className="p-4 sm:p-5 rounded-lg border border-[#E3E5EC] bg-white shadow-xs flex flex-col gap-4">
          <UnderlineTabs
            tabs={tabs}
            activeId={activeTab}
            onChange={(id) => setActiveTab(id)}
          />

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-start text-[13px] border-collapse">
              <thead>
                <tr className="bg-[#F8F9FC] border-b border-[#E3E5EC] text-[#6B7080] font-medium text-[12px] uppercase tracking-wider text-start">
                  <th className="py-3 px-3.5">Order no.</th>
                  <th className="py-3 px-3 w-16 text-center">Image</th>
                  <th className="py-3 px-4">Product Details</th>
                  <th className="py-3 px-4">Product ID</th>
                  <th className="py-3 px-4">Buyer & Destination</th>
                  <th className="py-3 px-4">Ordered on</th>
                  <th className="py-3 px-4">Amount</th>
                  {activeTab === "returns" && <th className="py-3 px-4">Return Reason</th>}
                  <th className="py-3 px-4 text-end">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E3E5EC]">
                {currentOrders.map((ord) => (
                  <tr
                    key={ord.id}
                    onClick={() => setSelectedOrderForDrawer(ord)}
                    className="hover:bg-[#F8F9FC]/80 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-3.5 font-mono text-[12px] font-semibold text-[#111827]">
                      {ord.orderNumber}
                    </td>

                    <td className="py-3.5 px-3 text-center">
                      <div className="size-12 mx-auto rounded-md overflow-hidden bg-gray-100 border border-[#E3E5EC]">
                        <img src={ord.thumbnailUrl} alt={ord.title} className="w-full h-full object-cover" />
                      </div>
                    </td>

                    <td className="py-3.5 px-4 max-w-[200px]">
                      <span className="font-semibold text-[#111827] line-clamp-1 group-hover:text-[#4B3BD1]">
                        {ord.title}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 font-mono text-[12px] text-[#4B3BD1] font-semibold">
                      <span className="flex items-center gap-1">
                        <QrCode className="size-3.5" />
                        <span>{ord.karuId}</span>
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-medium text-[#111827]">{ord.buyerName}</div>
                      <div className="text-[12px] text-[#6B7080] flex items-center gap-1">
                        <MapPin className="size-3 text-[#A3A7B5]" />
                        <span>{ord.buyerCity}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-[#6B7080] text-[12px] whitespace-nowrap">
                      {ord.orderedOn}
                    </td>

                    <td className="py-3.5 px-4 font-bold text-[#111827] whitespace-nowrap">
                      {inr(ord.priceInr)}
                    </td>

                    {activeTab === "returns" && (
                      <td className="py-3.5 px-4 text-[12px] text-[#B9532E] max-w-[180px]">
                        {ord.returnReason}
                      </td>
                    )}

                    <td className="py-3.5 px-4 text-end whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      {activeTab === "to_pack" && (
                        <button
                          type="button"
                          onClick={() => setShippingModalOrder(ord)}
                          className="px-3.5 py-1.5 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[12px] font-semibold transition-colors shadow-2xs"
                        >
                          Mark shipped
                        </button>
                      )}
                      {activeTab === "shipped" && (
                        <div className="text-[12px] text-[#16A34A] font-semibold flex items-center justify-end gap-1">
                          <Truck className="size-3.5" />
                          <span>{ord.courier}</span>
                        </div>
                      )}
                      {activeTab === "delivered" && (
                        <span className="text-[12px] text-[#16A34A] font-semibold">
                          ✓ Delivered
                        </span>
                      )}
                      {activeTab === "returns" && (
                        <button
                          type="button"
                          onClick={() => alert(`Confirmed return for ${ord.orderNumber}`)}
                          className="px-3 py-1.5 rounded-md border border-[#E3E5EC] bg-white hover:bg-[#F1F2F6] text-[#111827] text-[12px] font-semibold"
                        >
                          Confirm received
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Mark Shipped Modal with Courier + Tracking VoiceFields */}
      {shippingModalOrder && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 flex flex-col gap-4 animate-in fade-in duration-200 border border-[#E3E5EC]">
            <div className="flex items-center justify-between border-b border-[#E3E5EC] pb-3">
              <div className="flex items-center gap-2">
                <Truck className="size-5 text-[#4B3BD1]" />
                <h3 className="font-bold text-[16px] text-[#111827]">
                  Dispatch Order {shippingModalOrder.orderNumber}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShippingModalOrder(null)}
                className="text-[#6B7080] hover:text-[#111827]"
              >
                <X className="size-5" />
              </button>
            </div>

            <p className="text-[12.5px] text-[#6B7080]">
              Please confirm the courier partner and tracking reference for the package ({shippingModalOrder.karuId}).
            </p>

            <div className="flex flex-col gap-3">
              <VoiceField
                id="courier"
                label="Courier Partner"
                value={courierName}
                onChange={setCourierName}
                placeholder="e.g. Delhivery, BlueDart, India Post"
              />

              <VoiceField
                id="tracking"
                label="AWB / Tracking Number"
                value={trackingNumber}
                onChange={setTrackingNumber}
                placeholder="e.g. DEL-10928374"
              />
            </div>

            <div className="flex justify-end gap-2.5 pt-2 border-t border-[#E3E5EC]">
              <button
                type="button"
                onClick={() => setShippingModalOrder(null)}
                className="px-4 py-2 rounded-md border border-[#E3E5EC] text-[13px] font-medium text-[#111827] hover:bg-[#F1F2F6]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleMarkShipped}
                className="px-4 py-2 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13px] font-semibold"
              >
                Confirm Dispatch
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Order Detail Drawer */}
      {selectedOrderForDrawer && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-2xs transition-opacity"
            onClick={() => setSelectedOrderForDrawer(null)}
          />
          <div className="relative w-full max-w-md h-full bg-white shadow-2xl z-10 flex flex-col border-s border-[#E3E5EC] animate-in slide-in-from-right duration-200">
            <div className="p-4 border-b border-[#E3E5EC] flex items-center justify-between">
              <h3 className="font-bold text-[15px] text-[#111827]">
                Order Details · {selectedOrderForDrawer.orderNumber}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedOrderForDrawer(null)}
                className="p-1 rounded text-[#6B7080] hover:text-[#111827]"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-4 text-[13px]">
              <div className="flex gap-3 p-3 rounded-lg bg-[#F8F9FC] border border-[#E3E5EC]">
                <img
                  src={selectedOrderForDrawer.thumbnailUrl}
                  alt={selectedOrderForDrawer.title}
                  className="size-16 rounded object-cover"
                />
                <div>
                  <h4 className="font-semibold text-[#111827]">
                    {selectedOrderForDrawer.title}
                  </h4>
                  <p className="font-mono text-[#4B3BD1] font-semibold mt-0.5">
                    {selectedOrderForDrawer.karuId}
                  </p>
                  <p className="font-bold text-[#111827] mt-1">
                    {inr(selectedOrderForDrawer.priceInr)}
                  </p>
                </div>
              </div>

              <div className="flex flex-col gap-1 border-b border-[#E3E5EC] pb-3">
                <span className="text-[12px] font-semibold text-[#6B7080] uppercase">
                  Shipping Address
                </span>
                <p className="font-semibold text-[#111827]">
                  {selectedOrderForDrawer.buyerName}
                </p>
                <p className="text-[#5C554D] leading-normal">
                  {selectedOrderForDrawer.shipAddress || selectedOrderForDrawer.buyerCity}
                </p>
              </div>

              <div className="flex flex-col gap-1">
                <span className="text-[12px] font-semibold text-[#6B7080] uppercase">
                  Escrow Settlement Status
                </span>
                <p className="text-[#16A34A] font-semibold">
                  ✓ 100% Proceeds ({inr(selectedOrderForDrawer.priceInr)}) held safely in Meesho Escrow
                </p>
                <p className="text-[11.5px] text-[#6B7080]">
                  Released directly to your account immediately after delivery.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
