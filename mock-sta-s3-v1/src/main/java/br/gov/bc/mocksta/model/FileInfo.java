package br.gov.bc.mocksta.model;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Armazena o estado de cada protocolo:
 *  - arquivo temporário local (RandomAccessFile),
 *  - totalSize (tamanho informado no Content-Range ou tamanho do upload completo),
 *  - lista de intervalos já recebidos (List<RangeInterval>).
 */
public class FileInfo {
    private final String protocolo;
    private final File tempFile;
    private final RandomAccessFile raf;
    private long totalSize = -1; // definido no primeiro PUT com Content-Range ou no writeFull
    private final List<RangeInterval> receivedRanges = new ArrayList<>();

    public FileInfo(String protocolo) throws IOException {
        this.protocolo = protocolo;
        // Cria um arquivo temporário no diretório padrão (java.io.tmpdir)
        this.tempFile = File.createTempFile("mocksta_" + protocolo + "_", ".data");
        this.raf = new RandomAccessFile(this.tempFile, "rw");
    }

    public String getProtocolo() {
        return protocolo;
    }

    public long getTotalSize() {
        return totalSize;
    }

    public void setTotalSize(long totalSize) {
        this.totalSize = totalSize;
    }

    public File getTempFile() {
        return tempFile;
    }

    /**
     * Grava um fragmento do arquivo (bytes) a partir do offset “inicio”.
     * Atualiza lista de intervalos recebidos (receivedRanges).
     */
    public synchronized void writeChunk(long inicio, byte[] dados) throws IOException {
        raf.seek(inicio);
        raf.write(dados);

        long fim = inicio + dados.length - 1;
        RangeInterval novoIntervalo = new RangeInterval(inicio, fim);

        receivedRanges.add(novoIntervalo);
        mergeAdjacentIntervals();
    }

    /**
     * Grava o arquivo inteiro de uma vez (upload completo sem Content-Range).
     * Isso define totalSize = dados.length e substitui qualquer conteúdo anterior.
     */
    public synchronized void writeFull(byte[] dados) throws IOException {
        raf.setLength(0);
        raf.seek(0);
        raf.write(dados);

        this.totalSize = dados.length;
        receivedRanges.clear();
        receivedRanges.add(new RangeInterval(0, totalSize - 1));
    }

    /**
     * Retorna o sub-array de bytes entre [inicio, fim]. 
     * Se ainda não tiver gravado até “fim”, preenche com zeros os bytes faltantes.
     */
    public synchronized byte[] readRange(long inicio, long fim) throws IOException {
        long length = fim - inicio + 1;
        byte[] buffer = new byte[(int) length];
        raf.seek(inicio);
        int lido = raf.read(buffer);
        if (lido < length) {
            for (int i = lido; i < length; i++) {
                buffer[i] = 0;
            }
        }
        return buffer;
    }

    /**
     * Retorna todo o conteúdo já gravado (pode estar incompleto se upload ainda não finalizou).
     */
    public synchronized byte[] readFull() throws IOException {
        long tamanhoAtual = raf.length();
        byte[] buffer = new byte[(int) tamanhoAtual];
        raf.seek(0);
        raf.readFully(buffer);
        return buffer;
    }

    /**
     * Retorna uma lista imutável da lista de intervalos já recebidos.
     */
    public synchronized List<RangeInterval> getReceivedRanges() {
        return Collections.unmodifiableList(receivedRanges);
    }

    /**
     * Verifica se o upload já está 100% completo:
     * há exatamente um intervalo [0, totalSize-1] na lista.
     */
    public synchronized boolean isUploadComplete() {
        if (totalSize < 0) {
            return false;
        }
        if (receivedRanges.size() != 1) {
            return false;
        }
        RangeInterval intervalo = receivedRanges.get(0);
        return intervalo.getInicio() == 0 && intervalo.getFim() == totalSize - 1;
    }

    /**
     * Mescla intervalos sobrepostos ou adjacentes na lista receivedRanges.
     */
    private void mergeAdjacentIntervals() {
        if (receivedRanges.isEmpty()) return;

        receivedRanges.sort((a, b) -> Long.compare(a.getInicio(), b.getInicio()));
        List<RangeInterval> merged = new ArrayList<>();
        RangeInterval current = receivedRanges.get(0);

        for (int i = 1; i < receivedRanges.size(); i++) {
            RangeInterval next = receivedRanges.get(i);
            if (current.overlapsOrAdjacent(next)) {
                current = current.merge(next);
            } else {
                merged.add(current);
                current = next;
            }
        }
        merged.add(current);

        receivedRanges.clear();
        receivedRanges.addAll(merged);
    }

    /**
     * Fecha o RandomAccessFile e exclui o arquivo temporário local.
     * Deve ser chamado após o envio bem-sucedido ao S3.
     */
    public synchronized void cleanup() {
        try {
            raf.close();
        } catch (IOException ignored) {}
        tempFile.delete();
    }
}
