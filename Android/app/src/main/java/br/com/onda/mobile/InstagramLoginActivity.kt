package br.com.onda.mobile

import android.app.Activity
import android.os.Bundle
import android.view.View
import android.webkit.*
import android.widget.*
import org.json.JSONObject
import java.io.File

/** A native browser surface avoids WebView compositing failures inside Compose dialogs. */
class InstagramLoginActivity:Activity() {
    internal lateinit var browser:WebView
    private lateinit var status:TextView
    private lateinit var progress:ProgressBar
    private var loading=true

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        val bg=intent.getIntExtra("background",android.graphics.Color.BLACK)
        val fg=intent.getIntExtra("foreground",android.graphics.Color.WHITE)
        val accent=intent.getIntExtra("accent",0xff79e2c4.toInt())
        val inset=(12*resources.displayMetrics.density).toInt()
        val column=LinearLayout(this).apply {orientation=LinearLayout.VERTICAL;setPadding(inset,inset,inset,inset);setBackgroundColor(bg)}
        fun label(text:String,size:Float)=TextView(this).apply {this.text=translateUi(text);textSize=size;setTextColor(fg);setPadding(0,8,0,8)}
        column.addView(label("Conectar ao Instagram",20f))
        status=label("Entre no Instagram, conclua a verificação e toque em Usar esta sessão.",13f);column.addView(status)
        progress=ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal).apply {isIndeterminate=true};column.addView(progress,LinearLayout.LayoutParams(-1,8))
        browser=WebView(this)
        column.addView(browser,LinearLayout.LayoutParams(-1,0,1f))
        val density=resources.displayMetrics.density
        val gap=(8*density).toInt()
        val actions=LinearLayout(this).apply {orientation=LinearLayout.HORIZONTAL;gravity=android.view.Gravity.CENTER_VERTICAL;setPadding(0,gap,0,0)}
        fun button(text:String,primary:Boolean=false,action:()->Unit)=Button(this).apply {
            this.text=translateUi(text);isAllCaps=false;textSize=14f;minHeight=(48*density).toInt();minimumWidth=0
            setPadding(gap,gap,gap,gap);stateListAnimator=null
            setTextColor(if(primary)bg else accent)
            val shape=android.graphics.drawable.GradientDrawable().apply {
                cornerRadius=16*density;setColor(if(primary)accent else bg)
                if(!primary)setStroke((density+.5f).toInt(),accent)
            }
            background=android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(android.graphics.Color.argb(45,android.graphics.Color.red(fg),android.graphics.Color.green(fg),android.graphics.Color.blue(fg))),shape,null)
            setOnClickListener {action()}
        }
        actions.addView(button("Fechar"){finish()},LinearLayout.LayoutParams(0,-2,1f).apply {marginEnd=gap})
        actions.addView(button("Recarregar"){loading=true;progress.visibility=View.VISIBLE;browser.reload()},LinearLayout.LayoutParams(0,-2,1.4f).apply {marginEnd=gap})
        actions.addView(button("Usar esta sessão",primary=true){saveSession()},LinearLayout.LayoutParams(0,-2,1.9f))
        column.addView(actions);setContentView(column)
        browser.settings.apply {
            javaScriptEnabled=true;domStorageEnabled=true;allowFileAccess=false;allowContentAccess=false
            mixedContentMode=WebSettings.MIXED_CONTENT_NEVER_ALLOW
        }
        browser.webViewClient=object:WebViewClient() {
            override fun shouldOverrideUrlLoading(view:WebView,request:WebResourceRequest):Boolean = !instagramNavigationAllowed(request.url.scheme,request.url.host.orEmpty(),request.isForMainFrame)
            override fun onPageStarted(view:WebView,url:String?,icon:android.graphics.Bitmap?) {loading=true;progress.visibility=View.VISIBLE}
            override fun onPageFinished(view:WebView,url:String?) {loading=false;progress.visibility=View.GONE}
            override fun onReceivedError(view:WebView,request:WebResourceRequest,error:WebResourceError) {
                if(request.isForMainFrame){loading=false;progress.visibility=View.GONE;status.text=translateUi("Não foi possível carregar o Instagram. Toque em Recarregar para tentar novamente.")}
            }
        }
        CookieManager.getInstance().setAcceptCookie(true)
        browser.loadUrl("https://www.instagram.com/accounts/login/")
        browser.postDelayed({if(loading)status.text=translateUi("O Instagram está demorando para carregar. Toque em Recarregar para tentar novamente.")},25000)
    }

    private fun saveSession() {
        val manager=CookieManager.getInstance();manager.flush()
        val entries=instagramCookieEntries(listOf("https://www.instagram.com","https://instagram.com").map {manager.getCookie(it).orEmpty()})
        if(!hasInstagramLogin(entries)){status.text=translateUi("O login ainda não foi concluído. Entre na conta e aguarde o Instagram carregar.");return}
        try {
            val text=instagramCookieFile(entries)
            SecureVault.put("instagram-session",text)
            check(SecureVault.get("instagram-session")==text)
            File(filesDir,"instagram-session.txt").delete()
            OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("instagram_cookies_file","onda-vault:instagram"))
            setResult(RESULT_OK);finish()
        } catch(error:Exception) {status.text=translateUi("Não foi possível salvar a sessão. Tente novamente.")}
    }

    @Deprecated("Handled by native browser history")
    override fun onBackPressed() {if(browser.canGoBack())browser.goBack() else super.onBackPressed()}

    override fun onDestroy() {
        if(::browser.isInitialized){
            browser.stopLoading()
            clearWebSessionCookies(listOf("https://www.instagram.com","https://instagram.com"))
            WebStorage.getInstance().deleteOrigin("https://www.instagram.com")
            browser.destroy()
        }
        super.onDestroy()
    }
}
