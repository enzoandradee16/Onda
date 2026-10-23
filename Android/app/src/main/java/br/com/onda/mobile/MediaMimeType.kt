package br.com.onda.mobile

import java.util.Locale

/** Shared by MediaStore, SAF, opening files and the share sheet. */
internal fun mediaMimeType(name:String):String = when(name.substringAfterLast('.',"").lowercase(Locale.ROOT)) {
    "mp3"->"audio/mpeg"; "m4a"->"audio/mp4"; "aac"->"audio/aac"
    "flac"->"audio/flac"; "wav"->"audio/wav"; "ogg","opus"->"audio/ogg"
    "mov"->"video/quicktime"; "mp4","m4v"->"video/mp4"; "mkv"->"video/x-matroska"
    "webm"->"video/webm"; "avi"->"video/x-msvideo"; "mpeg","mpg"->"video/mpeg"
    "jpg","jpeg"->"image/jpeg"; "png"->"image/png"; "webp"->"image/webp"
    "svg"->"image/svg+xml"; "gif"->"image/gif"; "avif"->"image/avif"
    "bmp"->"image/bmp"; "heic"->"image/heic"; "heif"->"image/heif"
    else->"application/octet-stream"
}
