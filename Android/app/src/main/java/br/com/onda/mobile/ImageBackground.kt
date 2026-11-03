package br.com.onda.mobile

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** CPU inference is bounded to one worker and releases the model after use. */
object ImageBackground {
    @JvmStatic fun predict(model:String, input:ByteArray):ByteArray {
        require(input.size==3*320*320*4)
        val environment=OrtEnvironment.getEnvironment()
        OrtSession.SessionOptions().use {options->
            options.setIntraOpNumThreads(1);options.setInterOpNumThreads(1)
            options.addConfigEntry("session.intra_op.allow_spinning","0")
            options.addConfigEntry("session.inter_op.allow_spinning","0")
            environment.createSession(model,options).use {session->
                val floats=ByteBuffer.wrap(input).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
                OnnxTensor.createTensor(environment,floats,longArrayOf(1,3,320,320)).use {tensor->
                    session.run(mapOf(session.inputNames.first() to tensor)).use {result->
                        val output=(result.get(0) as OnnxTensor).floatBuffer
                        require(output.remaining()==320*320)
                        val data=FloatArray(output.remaining());output.get(data)
                        return ByteBuffer.allocate(data.size*4).order(ByteOrder.LITTLE_ENDIAN).apply {asFloatBuffer().put(data)}.array()
                    }
                }
            }
        }
    }
}
