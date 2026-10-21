package br.com.onda.mobile
import org.junit.Assert.*
import org.junit.Test

class HistoryGroupingTest {
    @Test fun formatsAreFilteredWithoutLosingUnknownDownloads(){
        assertEquals("Áudio",historyKind("MP3"));assertEquals("Áudio",historyKind("original"))
        assertEquals("Imagens",historyKind("webp"));assertEquals("Imagens",historyKind("photos"))
        assertEquals("Vídeo",historyKind("mkv"));assertEquals("Vídeo",historyKind("social"))
    }
    @Test fun oldHistoryNeverGetsAnInventedDownloadDate(){assertEquals("Anteriores",historyDay(0))}
    @Test fun todayAndYesterdayUseLocalDates(){
        val zone=java.time.ZoneId.systemDefault()
        val now=java.time.LocalDate.of(2026,10,21).atTime(12,0).atZone(zone).toInstant().toEpochMilli()
        assertEquals("Hoje",historyDay(now,now));assertEquals("Ontem",historyDay(now-86400000,now))
        assertEquals("19/10/2026",historyDay(now-172800000,now))
    }
}
