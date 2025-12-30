
import './style.css';
import { marked } from 'marked';

let totalSessionCost: number = 0;

const costDisplay = document.getElementById('cost-display') as HTMLElement;

const chatBox = document.getElementById('chat-box') as HTMLDivElement;
const userInput = document.getElementById('user-input') as HTMLInputElement;
const sendBtn = document.getElementById('send-btn') as HTMLButtonElement;
const sourcesList = document.getElementById('sources-list') as HTMLDivElement; 
const clearBtn = document.getElementById('clear-btn') as HTMLButtonElement;
const modal = document.getElementById('modal-overlay') as HTMLDivElement;
const modalConfirmBtn = document.getElementById('modal-confirm') as HTMLButtonElement;
const modalCancelBtn = document.getElementById('modal-cancel') as HTMLButtonElement;
const thresholdInput = document.getElementById('threshold-range') as HTMLInputElement;
const currentThreshold = thresholdInput ? parseFloat(thresholdInput.value) : 0.5;
const rangeInput = document.getElementById('threshold-range') as HTMLInputElement;
const rangeValue = document.getElementById('threshold-value') as HTMLSpanElement;

const contextModal = document.getElementById('context-modal') as HTMLElement;
const contextText = document.getElementById('context-text') as HTMLElement;
const contextFileName = document.getElementById('context-filename') as HTMLElement;
const contextPage = document.getElementById('context-page') as HTMLElement;
const closeContextBtn = document.getElementById('close-context') as HTMLElement;

rangeInput.addEventListener('input', (e) => {
    rangeValue.innerText = parseFloat((e.target as HTMLInputElement).value).toFixed(2);
});

function showConfirmModal(message: string): Promise<boolean> {
    return new Promise((resolve) => {
        const modalText = document.getElementById('modal-text') as HTMLParagraphElement;
        modalText.innerText = message;
        modal.classList.remove('hidden');

        const cleanup = (result: boolean) => {
            modal.classList.add('hidden');
            modalConfirmBtn.removeEventListener('click', onConfirm);
            modalCancelBtn.removeEventListener('click', onCancel);
            resolve(result);
        };

        const onConfirm = () => cleanup(true);
        const onCancel = () => cleanup(false);

        modalConfirmBtn.addEventListener('click', onConfirm);
        modalCancelBtn.addEventListener('click', onCancel);
    });
}

function updateTotalCost(queryCost: number){
    console.log("Custo recebido da API:", queryCost);
    if (isNaN(queryCost)) return;

    totalSessionCost += queryCost;

    if (costDisplay) {
        costDisplay.innerText = totalSessionCost.toFixed(6);
        costDisplay.classList.add('text-green-600');
        setTimeout(()=> costDisplay.classList.remove('text-green-600'), 500);
    }else {
        console.error("Erro: Não encontrei o elemento 'cost-display' no HTML.");
    }
}

function getLoadingHTML() {
    return `
        <div class="flex space-x-1 h-4 items-center">
            <div class="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
        </div>
    `;
}

function addmessage(content: string, isUser: boolean, isHTML: boolean = false) {
    const wrapper = document.createElement('div');
    wrapper.className = `flex ${isUser ? 'justify-end' : 'justify-start'} animate-enter`;
    
    const bubble = document.createElement('div');
    const baseClasses = "max-w-[80%] p-4 rounded-2xl shadow-sm text-[15px] mb-2 ";

    if (isUser) {
        bubble.className = "bg-black text-white px-5 py-3.5 rounded-2xl rounded-tr-sm max-w-[80%] shadow-md text-[14px] leading-relaxed";
    } else {
       bubble.className = "bg-white text-gray-800 px-6 py-4 rounded-2xl rounded-tl-sm border border-gray-100 shadow-sm max-w-[85%] text-[14px] leading-relaxed";
    }

    if (isHTML){
        bubble.innerHTML = content;
    } else if (isUser) {
        bubble.innerText = content;
    } else {
        bubble.innerHTML = marked.parse(content) as string;
    }

    wrapper.appendChild(bubble);
    chatBox.appendChild(wrapper);
    
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
    return bubble;
}

function updateSources(sources: any[]) {
    if (!sources || sources.length === 0) {
        sourcesList.innerHTML = `
            <div class="text-center p-6 border-2 border-dashed border-gray-200 rounded-xl">
                <p class="text-xs text-gray-400">Nenhuma referência ativa</p>
            </div>`;
        return;
    }

    sourcesList.innerHTML = "";
    sources.forEach((src: any) => {
        const card = document.createElement('div');
        card.className = "group p-3 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all cursor-default animate-enter";
        
        card.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="bg-red-50 text-red-500 p-1.5 rounded-md">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-semibold text-gray-700 truncate" title="${src.file}">${src.file}</p>
                    <p class="text-[10px] text-gray-400 mt-0.5">Página ${src.page}</p>
                </div>
            </div>
        `;
        sourcesList.appendChild(card);
    });
}

async function askToAPI() {
    const question = userInput.value.trim();
    if (!question) return;

    const currentThresholdValue = parseFloat(rangeInput.value);


    addmessage(question, true);
    userInput.value = "";

    const loadingBubble = addmessage(getLoadingHTML(), false, true);


    try { 
        const response = await fetch(`http://localhost:8000/ask`,{
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                threshold: currentThresholdValue
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();

        loadingBubble.innerHTML = "";

        const parsedMarkdown = await marked.parse(data.answer || data.response);
        let responseHTML = `<div class="mb-3 prose prose-sm max-w-none text-gray-900">${marked.parse(data.answer)}</div>`;

        if (data.estimated_cost){
            updateTotalCost(data.estimated_cost);
        }
        
        if (data.sources && data.sources.length > 0) {
                    responseHTML += `
            <div class="mt-4 pt-3 border-t border-gray-100">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-2">Fontes consultadas (clique para ver o trecho):</p>
                <div class="flex flex-wrap gap-2">
                    ${data.sources.map((src: any) => `
                        <span 
                            onclick="openContext('${src.file}', '${src.page}', '${src.content.replace(/'/g, "\\'")}')"
                            class="cursor-pointer hover:bg-black hover:text-white transition-all inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-600 text-[10px] rounded-md border border-gray-200"
                        >
                            <svg class="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                            ${src.file} (p. ${src.page})
                        </span>
                    `).join('')}
                </div>
            </div>`;
    }
    loadingBubble.innerHTML = responseHTML;
        
    }
    catch (error) {
        console.error('There was a problem with the fetch operation:', error);
        addmessage("Desculpe, houve um erro com sua resposta.", false);
    }
}

async function loadStoredDocuments() {
    const sourcesList = document.getElementById('sources-list') as HTMLDivElement;
    
    sourcesList.innerHTML = `<div class="p-4 text-center"><div class="typing-dot bg-gray-300 w-2 h-2 inline-block rounded-full"></div></div>`;

    try {
        const response = await fetch('http://localhost:8000/documents');
        if (!response.ok) throw new Error('Network response was not ok');

        const data = await response.json();
        const docs = data.documents;

        sourcesList.innerHTML = "";

        if (docs.length === 0) {
            sourcesList.innerHTML = `
            <div class="text-center p-6 border-2 border-dashed border-gray-200 rounded-xl">
                    <p class="text-xs text-gray-400">Nenhum documento indexado</p>
                </div>`;
            return;
        }

        docs.forEach((docName: string) => {

            const card = document.createElement('div');
            card.className = "group flex items-center gap-3 p-3 mb-2 bg-white border border-gray-100 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all cursor-default";
            
            card.innerHTML = `
                <div class="bg-gray-50 text-gray-500 group-hover:text-black group-hover:bg-gray-100 p-2 rounded-lg transition-colors">
        <svg class="w-4 h-4" ...></svg>
    </div>
    <span class="text-xs font-medium text-gray-600 group-hover:text-gray-900 truncate flex-1">${docName}</span>
    <button class="delete-doc-btn p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12"></path></svg>
    </button>
    <div class="w-2 h-2 rounded-full bg-green-400" title="Indexado e pronto"></div>
                `;

            card.querySelector('.delete-doc-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteDocument(docName);
            });

            sourcesList.appendChild(card);
        });
    } catch (error) {
        console.error('There was a problem fetching documents:', error);
        sourcesList.innerHTML = `<p class="text-xs text-red-400 px-4">Erro de conexão com o banco.</p>`;
    }
}

async function deleteDocument(fileName: string) {
    const confirmed = await showConfirmModal(`Tem certeza que deseja deletar o documento "${fileName}"? Esta ação não pode ser desfeita.`);
    if (!confirmed) return;

    try {
        const response = await fetch(`http://localhost:8000/documents/${encodeURIComponent(fileName)}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            addmessage(`🗑️ Documento "${fileName}" deletado.`, false);
            await loadStoredDocuments();
        } else {
            alert("Erro ao deletar documento.");
        }
    } catch (e) {
        console.error(e);
        alert("Erro ao deletar:", e);
    }
}



sendBtn.addEventListener('click', askToAPI)
userInput.addEventListener('keypress', async (e) => {
 if (e.key === 'Enter') askToAPI();
});    

const fileInput = document.getElementById('file-upload') as HTMLInputElement;

fileInput.addEventListener('change', async () => {
    const files = fileInput.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    const originalSidebarHTML = sourcesList.innerHTML;
    sourcesList.innerHTML = `
        <div class="p-4 bg-gray-50 border border-gray-100 rounded-xl">
            <p id="upload-status" class="text-[10px] font-bold text-gray-500 uppercase">Processando...</p>
            <div class="w-full bg-gray-200 h-1.5 mt-2 rounded-full overflow-hidden">
                <div id="progress-bar" class="bg-black h-full w-0 transition-all duration-300"></div>
            </div>
        </div>`;
    
    const bar = document.getElementById('progress-bar') as HTMLDivElement;
    const status = document.getElementById('upload-status') as HTMLParagraphElement;

    try {
        const response = await fetch('http://localhost:8000/upload-pdfs', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error('Falha no upload dos arquivos.');
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (reader) {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                const lines = chunk.split(`\n`);
                lines.forEach(line => {
                        if (line.includes('data: ')) {
                            const data = line.replace('data: ', '').trim();
                            const [statusMsg, progrssVal] = data.split('|');

                            if (statusMsg && status) status.innerText = statusMsg.replace('status:', '');
                            if (progrssVal) {
                                const percent = progrssVal.replace('progress:', '');
                                bar.style.width = `${percent}%`;
                            }
                }
            
            });
        }
    }


        addmessage(`📂 ${files.length} arquivo(s) processados com sucesso.`, false);
        await loadStoredDocuments();

        fileInput.value = "";
    }
    catch (error) {
        console.error('Erro durante o upload:', error);
        addmessage("⚠️ Ocorreu um erro ao processar os PDFs. Verifique o console.", false);
        sourcesList.innerHTML = originalSidebarHTML;
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadStoredDocuments();
});

clearBtn.addEventListener('click', async () => {
    if (!await showConfirmModal("Tem certeza? Isso apagará todo o conhecimento da IA.")) return;

    try {
        const btnContent = clearBtn.innerHTML;
        clearBtn.innerHTML = `<span class="text-xs">Limpando...</span>`;
        clearBtn.disabled = true;

        const response = await fetch('http://localhost:8000/clear-database', {
            method: 'DELETE'
        });

        if (response.ok) {
            addmessage("🧹 A memória do sistema foi apagada.", false);
            // Atualiza a sidebar para mostrar que está vazia
            await loadStoredDocuments(); 
        } else {
            alert("Erro ao limpar banco.");
        }

        clearBtn.innerHTML = btnContent;
        clearBtn.disabled = false;

    } catch (e) {
        console.error(e);
        alert("Erro de conexão.");
        clearBtn.disabled = false;
    }
});

if (closeContextBtn){
    closeContextBtn.onclick = () => contextModal.classList.add('hidden');
}

(window as any).openContext = (file: string, page: string, content: string) => {
    if (contextFileName && contextPage && contextText && contextModal) {
        contextFileName.innerText = file;
        contextPage.innerText = `Página ${page}`;
        contextText.innerText = `"${content}"`;
        contextModal.classList.remove('hidden');
    }
};