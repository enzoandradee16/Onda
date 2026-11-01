package br.com.onda.mobile

/** Avoid repeated JNI writes; a new output and failed writes always retry. */
internal class AppliedAudioGain {
    private var output:Any?=null
    private var gain=Float.NaN
    @Synchronized fun apply(target:Any,value:Float,write:(Float)->Int) {
        if(output===target && gain==value)return
        if(write(value)==0){output=target;gain=value}
    }
    @Synchronized fun clear(target:Any?=null) {
        if(target==null || output===target){output=null;gain=Float.NaN}
    }
}
