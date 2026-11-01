import QtQuick
ListModel {
    id: stable
    dynamicRoles: true
    property var rows: []
    onRowsChanged: reconcile()
    function reconcile() {
        var wanted = {}
        for (var i=0;i<rows.length;++i) wanted[rows[i].id]=true
        for (var old=count-1;old>=0;--old)
            if (!wanted[get(old).modelData.id]) remove(old)
        for (var target=0;target<rows.length;++target) {
            var row=rows[target]
            var found=-1
            for (var j=target;j<count;++j)
                if (get(j).modelData.id===row.id) { found=j;break }
            if (found<0) insert(target,{modelData:row,group:row.group || ""})
            else {
                if (found!==target) move(found,target,1)
                if (JSON.stringify(get(target).modelData)!==JSON.stringify(row))
                    set(target,{modelData:row,group:row.group || ""})
            }
        }
    }
}
