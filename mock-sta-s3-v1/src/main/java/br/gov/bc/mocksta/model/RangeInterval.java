package br.gov.bc.mocksta.model;

/**
 * Intervalo de bytes recebido para um protocolo: [inicio, fim].
 */
public class RangeInterval {
    private final long inicio;
    private final long fim;

    public RangeInterval(long inicio, long fim) {
        this.inicio = inicio;
        this.fim = fim;
    }

    public long getInicio() {
        return inicio;
    }

    public long getFim() {
        return fim;
    }

    /**
     * Verifica se este intervalo se sobrepõe ou é adjacente a outro.
     * Útil para “colar” intervalos contíguos automaticamente.
     */
    public boolean overlapsOrAdjacent(RangeInterval outro) {
        return !(this.fim + 1 < outro.inicio || outro.fim + 1 < this.inicio);
    }

    /**
     * Mescla dois intervalos que se sobrepõem ou são adjacentes.
     * Pré-condição: overlapsOrAdjacent(outro) == true.
     */
    public RangeInterval merge(RangeInterval outro) {
        long novoInicio = Math.min(this.inicio, outro.inicio);
        long novoFim = Math.max(this.fim, outro.fim);
        return new RangeInterval(novoInicio, novoFim);
    }
}
