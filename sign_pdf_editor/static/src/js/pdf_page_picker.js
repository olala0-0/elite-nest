/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, useRef, useState, onMounted, onWillUnmount } from "@odoo/owl";

// Odoo's web client has bundled pdf.js for report/document previews since
// long before v19; this is the well-known static path. If your instance
// serves it from somewhere else, the error banner below will say so -
// tell me the exact failing URL from the browser console and I'll adjust
// this constant, since I can't inspect your live assets from here.
const PDFJS_URL = "/web/static/lib/pdfjs/build/pdf.js";
const PDFJS_WORKER_URL = "/web/static/lib/pdfjs/build/pdf.worker.js";

const PAGE_FIELDS = {
    add_text: { page: "text_page", x: "text_pos_x", y: "text_pos_y" },
    add_image: { page: "image_page", x: "image_pos_x", y: "image_pos_y" },
};

export class PdfPagePicker extends Component {
    static template = "sign_pdf_editor.PdfPagePicker";
    static props = { ...standardWidgetProps };

    setup() {
        this.canvasRef = useRef("canvas");
        this.state = useState({
            loading: false,
            error: null,
            pageCount: 0,
            marker: null,
        });
        this._pdfDoc = null;
        this._loadedForTemplateId = null;
        onMounted(() => this._refresh());
        onWillUnmount(() => {
            this._pdfDoc = null;
        });
    }

    get fieldNames() {
        const operation = this.props.record.data.operation;
        return PAGE_FIELDS[operation] || null;
    }

    get isApplicable() {
        return !!this.fieldNames && !!this._templateId;
    }

    get _templateId() {
        const value = this.props.record.data.template_id;
        if (!value) {
            return false;
        }
        // Relational field value shape has varied across Odoo versions
        // (plain [id, name] tuple vs. a Record-like object) - handle both.
        if (Array.isArray(value)) {
            return value[0];
        }
        return value.resId || value.id || false;
    }

    async _refresh() {
        if (!this.isApplicable) {
            return;
        }
        this.state.error = null;
        if (this._loadedForTemplateId !== this._templateId) {
            await this._loadPdf();
        }
        await this._renderCurrentPage();
    }

    async onOperationOrTemplateChanged() {
        await this._refresh();
    }

    async _loadPdf() {
        this.state.loading = true;
        try {
            await loadJS(PDFJS_URL);
            if (window.pdfjsLib && window.pdfjsLib.GlobalWorkerOptions) {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_URL;
            }
            const url = `/sign_pdf_editor/preview/${this._templateId}`;
            const loadingTask = window.pdfjsLib.getDocument(url);
            this._pdfDoc = await loadingTask.promise;
            this.state.pageCount = this._pdfDoc.numPages;
            this._loadedForTemplateId = this._templateId;
        } catch (e) {
            this.state.error = (
                "Could not load the PDF preview (pdf.js at '" + PDFJS_URL + "' " +
                "may not exist on this instance). You can still use the " +
                "Page/X/Y number fields below. Error: " + (e && e.message ? e.message : e)
            );
            this._pdfDoc = null;
        } finally {
            this.state.loading = false;
        }
    }

    async _renderCurrentPage() {
        if (!this._pdfDoc || !this.canvasRef.el) {
            return;
        }
        const fields = this.fieldNames;
        let pageNum = (fields && this.props.record.data[fields.page]) || 1;
        pageNum = Math.min(Math.max(parseInt(pageNum, 10) || 1, 1), this.state.pageCount);
        try {
            const page = await this._pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: 1.3 });
            const canvas = this.canvasRef.el;
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const ctx = canvas.getContext("2d");
            await page.render({ canvasContext: ctx, viewport }).promise;
            this.state.marker = null;
        } catch (e) {
            this.state.error = "Could not render page " + pageNum + ": " + (e && e.message ? e.message : e);
        }
    }

    async onPrevPage() {
        await this._changePage(-1);
    }

    async onNextPage() {
        await this._changePage(1);
    }

    async _changePage(delta) {
        const fields = this.fieldNames;
        if (!fields) {
            return;
        }
        const current = parseInt(this.props.record.data[fields.page], 10) || 1;
        const next = Math.min(Math.max(current + delta, 1), this.state.pageCount || 1);
        await this.props.record.update({ [fields.page]: next });
        await this._renderCurrentPage();
    }

    async onRefreshClick() {
        await this._refresh();
    }

    async onCanvasClick(ev) {
        const fields = this.fieldNames;
        if (!fields) {
            return;
        }
        const canvas = this.canvasRef.el;
        const rect = canvas.getBoundingClientRect();
        const xPct = ((ev.clientX - rect.left) / rect.width) * 100;
        const yPct = ((ev.clientY - rect.top) / rect.height) * 100;
        this.state.marker = {
            left: ev.clientX - rect.left,
            top: ev.clientY - rect.top,
        };
        await this.props.record.update({
            [fields.x]: Math.round(xPct * 100) / 100,
            [fields.y]: Math.round(yPct * 100) / 100,
        });
    }
}

registry.category("view_widgets").add("pdf_page_picker", {
    component: PdfPagePicker,
});
