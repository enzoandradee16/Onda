package br.com.onda.mobile

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.ln

internal val equalizerLayouts = linkedMapOf(
    5 to listOf(63.0,250.0,1000.0,4000.0,16000.0),
    10 to listOf(31.25,62.5,125.0,250.0,500.0,1000.0,2000.0,4000.0,8000.0,16000.0),
    15 to listOf(25.0,40.0,63.0,100.0,160.0,250.0,400.0,630.0,1000.0,1600.0,2500.0,4000.0,6300.0,10000.0,16000.0)
)

private fun bounded(value:Double, fallback:Double, low:Double, high:Double)=
    if(value.isFinite())value.coerceIn(low,high) else fallback

internal fun cleanEqualizerSettings(value:JSONObject?):JSONObject {
    val input=value ?: JSONObject()
    val bands=input.optJSONArray("bands") ?: JSONArray()
    val inferred=bands.length().takeIf {it in equalizerLayouts} ?: 10
    val rawCount=input.opt("band_count")
    val count=if(!input.has("band_count"))inferred else (rawCount as? Int)?.takeIf {it in equalizerLayouts} ?: 10
    return JSONObject().put("enabled",input.opt("enabled")==true)
        .put("preamp",bounded(input.optDouble("preamp",-6.0),-6.0,-24.0,0.0))
        .put("band_count",count).put("bands",JSONArray().apply {
            equalizerLayouts.getValue(count).forEachIndexed {index,frequency->
                val row=bands.optJSONObject(index) ?: JSONObject()
                put(JSONObject().put("frequency",bounded(row.optDouble("frequency",frequency),frequency,20.0,20000.0))
                    .put("gain",bounded(row.optDouble("gain",0.0),0.0,-12.0,12.0))
                    .put("q",bounded(row.optDouble("q",1.4),1.4,.1,10.0)))
            }
        })
}

internal fun resizeEqualizerSettings(input:JSONObject,count:Int):JSONObject {
    val value=cleanEqualizerSettings(input)
    if(count !in equalizerLayouts || count==value.getInt("band_count"))return value
    val rows=value.getJSONArray("bands")
    val points=(0 until rows.length()).map {rows.getJSONObject(it)}.associateBy {it.getDouble("frequency")}.toSortedMap().entries.toList()
    fun interpolate(frequency:Double,key:String):Double {
        if(frequency<=points.first().key)return points.first().value.getDouble(key)
        for((left,right) in points.zipWithNext())if(frequency<=right.key) {
            val weight=ln(frequency/left.key)/ln(right.key/left.key)
            return left.value.getDouble(key)+weight*(right.value.getDouble(key)-left.value.getDouble(key))
        }
        return points.last().value.getDouble(key)
    }
    val bands=JSONArray().apply {equalizerLayouts.getValue(count).forEach {frequency->
        put(JSONObject().put("frequency",frequency).put("gain",interpolate(frequency,"gain")).put("q",interpolate(frequency,"q")))
    }}
    return cleanEqualizerSettings(value.put("band_count",count).put("bands",bands))
}

internal fun equalizerPreset(row:JSONObject,count:Int)=resizeEqualizerSettings(
    JSONObject().put("enabled",true).put("preamp",row.getDouble("preamp"))
        .put("bands",JSONArray().apply {
            val gains=row.getJSONArray("gains")
            for(index in 0 until gains.length())put(JSONObject().put("gain",gains.getDouble(index)))
        }),count)
