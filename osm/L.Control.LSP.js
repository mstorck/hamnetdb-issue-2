L.Control.LSP = L.Control.extend(
{
    options:
    {
        position: 'topright'
    },
    onAdd: function (map) {
        var toolDiv = L.DomUtil.create('div', 'toolbar');
        var infoDiv = L.DomUtil.create('div', 'info-toolbar',toolDiv);
        L.DomEvent
            .addListener(infoDiv, 'click', L.DomEvent.stopPropagation)
            .addListener(infoDiv, 'click', L.DomEvent.preventDefault)
        .addListener(infoDiv, 'click', function () {
            SidebarSetting.hide();
            SidebarInfo.toggle();
        });

        var controlUI = L.DomUtil.create('a', 'info-toolbar-a', infoDiv);
        controlUI.title = 'show Info';
        controlUI.href = 'javascript:SidebarInfo.toggle()';
        controlUI.innerHTML = "";
        
        
        var settingDiv = L.DomUtil.create('div', 'setting-toolbar',toolDiv);
        L.DomEvent
            .addListener(settingDiv, 'click', L.DomEvent.stopPropagation)
            .addListener(settingDiv, 'click', L.DomEvent.preventDefault)
        .addListener(settingDiv, 'click', function () {
            SidebarInfo.hide();
            SidebarSetting.toggle();
        });

        var controlUI = L.DomUtil.create('a', 'setting-toolbar-a', settingDiv);
        controlUI.title = 'show Settings';
        controlUI.href = 'javascript:SidebarSetting.toggle()';
        controlUI.innerHTML = "";
        //return settingDiv;
        
        return toolDiv;
    },
    _createInfo: function () {
        
        
    }
});
