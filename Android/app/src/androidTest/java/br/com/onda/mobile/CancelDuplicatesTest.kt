package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class CancelDuplicatesTest {
    @Test fun cancelAllPreservesOriginalsUniqueTracksAndUnrelatedQuestions() {
        val token=UUID.randomUUID().toString()
        val options=JSONObject(OndaStore.settings.value.toString()).put("detect_duplicates",true).put("mode","mp3").put("link_playlist",false)
        val batch=JSONObject(options.toString()).put("_duplicate_batch",token)
        val ids=mutableSetOf<String>()
        val unrelated="unrelated-$token"
        try {
            val original=OndaStore.enqueue("https://example.com/$token/song","Original",options);ids.add(original)
            val duplicate=OndaStore.enqueue("https://example.com/$token/song","Duplicate",batch);ids.add(duplicate)
            val unique=OndaStore.enqueue("https://example.com/$token/unique","Unique",batch);ids.add(unique)
            OndaStore.ask(unrelated,JSONObject().put("type","choose_version"))
            assertEquals("Duplicata",OndaStore.items.value.first {it.id==duplicate}.state)
            OndaStore.cancelAllDuplicates()
            assertFalse(OndaStore.items.value.any {it.id==duplicate})
            assertTrue(OndaStore.items.value.any {it.id==original})
            assertTrue(OndaStore.items.value.any {it.id==unique})
            assertEquals(unrelated,OndaStore.question.value?.identity)
            assertEquals("",OndaStore.enqueue("https://example.com/$token/song","Later chunk",batch))
            val next=OndaStore.enqueue("https://example.com/$token/song","New batch",JSONObject(options.toString()).put("_duplicate_batch","next-$token"))
            ids.add(next)
            assertTrue(next.isNotBlank())
            assertEquals("Duplicata",OndaStore.items.value.first {it.id==next}.state)
        } finally {
            OndaStore.dismissQuestions(unrelated)
            ids.forEach {OndaStore.dismissQuestions("duplicate-$it")}
            OndaStore.remove(ids)
        }
    }
}
