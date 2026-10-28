package br.com.onda.mobile

import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.Process
import android.view.Gravity
import android.widget.TextView

/** Foreground handoff in a private process; no alarms or background launch needed. */
class RestartActivity : Activity() {
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        val dark=intent.getBooleanExtra("dark",true)
        setContentView(TextView(this).apply {
            text=intent.getStringExtra("message").orEmpty();textSize=18f;gravity=Gravity.CENTER
            setBackgroundColor(if(dark)Color.BLACK else Color.WHITE)
            setTextColor(if(dark)Color.WHITE else Color.BLACK)
        })
        val pid=intent.getIntExtra("parent_pid",-1)
        val manager=getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val own=manager.runningAppProcesses.orEmpty().any {it.pid==pid&&it.uid==Process.myUid()&&it.processName==packageName}
        if(!own||pid==Process.myPid()) {finish();return}
        val handler=Handler(Looper.getMainLooper())
        handler.postDelayed({
            Process.killProcess(pid)
            var attempts=0
            val reopen=object:Runnable {
                override fun run() {
                    if(manager.runningAppProcesses.orEmpty().any {it.pid==pid} && attempts++<30) {handler.postDelayed(this,100);return}
                    if(manager.runningAppProcesses.orEmpty().any {it.pid==pid}) {finish();return}
                    startActivity(Intent(this@RestartActivity,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
                    finish()
                    handler.postDelayed({Process.killProcess(Process.myPid())},500)
                }
            }
            handler.postDelayed(reopen,150)
        },250)
    }
}

internal fun isRestartProcess(context:Context):Boolean {
    val name=if(android.os.Build.VERSION.SDK_INT>=28)android.app.Application.getProcessName() else
        (context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager).runningAppProcesses.orEmpty().firstOrNull {it.pid==Process.myPid()}?.processName
    return name==context.packageName+":restart"
}
