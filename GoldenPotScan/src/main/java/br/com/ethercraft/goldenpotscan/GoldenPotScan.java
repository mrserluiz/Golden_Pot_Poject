package br.com.ethercraft.goldenpotscan;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.command.*;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.Player;
import org.bukkit.event.*;
import org.bukkit.event.inventory.*;
import org.bukkit.inventory.*;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.EnchantmentStorageMeta;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.java.JavaPlugin;
import java.io.File;
import java.io.IOException;
import java.text.Normalizer;
import java.util.*;

public final class GoldenPotScan extends JavaPlugin implements Listener, CommandExecutor, TabCompleter {
    private final Map<UUID,String> pending=new HashMap<>();
    private final Map<String,YamlConfiguration> menus=new HashMap<>();
    private final Map<String,ItemStack> gemTemplates=new HashMap<>();
    private final Map<String,Integer> bookCmd=new LinkedHashMap<>();
    private File menusDir,templatesFile;
    private boolean visual, itemEnabled, logging;
    @Override public void onEnable(){
        saveDefaultConfig();
        menusDir=new File(getDataFolder(),"menus"); if(!menusDir.exists()&&!menusDir.mkdirs()) getLogger().warning("Unable to create menus directory");
        templatesFile=new File(getDataFolder(),"gem-templates.yml");
        visual=getConfig().getBoolean("menu-manager.visual-enabled",false);
        logging=getConfig().getBoolean("menu-manager.log",false);
        itemEnabled=getConfig().getBoolean("item-manager.enabled",false);
        initBookRules();loadTemplates();loadMenus();
        Objects.requireNonNull(getCommand("goldenpotscan")).setExecutor(this);
        Objects.requireNonNull(getCommand("goldenpotscan")).setTabCompleter(this);
        Bukkit.getPluginManager().registerEvents(this,this);
        long interval=Math.max(20,getConfig().getLong("item-manager.scan-period-ticks",40));
        Bukkit.getScheduler().runTaskTimer(this,this::scanAll,interval,interval);
        getLogger().info("GoldenPotScan v0.0.1 enabled: menus="+menus.size()+", item scan="+itemEnabled+", visual="+visual);
    }
    private void log(String value){if(logging)getLogger().info(value);}
    private String plain(String legacy){return org.bukkit.ChatColor.stripColor(legacy==null?"":legacy);}
    private String menuTitle(InventoryView view){return plain(view.getTitle());}
    private String idFor(InventoryView view){
        String title=menuTitle(view);int size=view.getTopInventory().getSize();
        for(var e:menus.entrySet()) if(title.equals(e.getValue().getString("recognition.title"))&&size==e.getValue().getInt("recognition.size"))return e.getKey();
        return null;
    }
    private String safeId(String input){
        String value=Normalizer.normalize(input,Normalizer.Form.NFD).replaceAll("\\p{M}","").toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_-]+","_").replaceAll("^_+|_+$","");
        if(value.length()>60)value=value.substring(0,60);
        return value.isEmpty()?"menu":value;
    }
    private void loadMenus(){
        menus.clear();File[] files=menusDir.listFiles((d,n)->n.endsWith(".yml"));if(files==null)return;
        for(File file:files){YamlConfiguration yaml=YamlConfiguration.loadConfiguration(file);if(yaml.getString("recognition.title")==null||yaml.getInt("recognition.size")<=0){getLogger().warning("Invalid menu: "+file.getName());continue;}menus.put(file.getName().substring(0,file.getName().length()-4),yaml);}
    }
    private void capture(Player player,String requested){
        InventoryView view=player.getOpenInventory();Inventory inv=view.getTopInventory();
        if(inv.getType()==InventoryType.CRAFTING||inv.getType()==InventoryType.PLAYER){player.sendMessage("§cOpen a plugin menu, not the player inventory.");return;}
        String title=menuTitle(view),id="auto".equals(requested)?safeId(title):safeId(requested);
        if("auto".equals(requested)){
            String existing=idFor(view);if(existing!=null)id=existing;
            else{String base=id;int suffix=2;while(menus.containsKey(id)||new File(menusDir,id+".yml").exists())id=base+"_"+suffix++;}
        }
        File file=new File(menusDir,id+".yml");YamlConfiguration yaml=new YamlConfiguration();
        if(file.exists()){YamlConfiguration previous=YamlConfiguration.loadConfiguration(file);ConfigurationSection old=previous.getConfigurationSection("visual.slots");if(old!=null)for(String slot:old.getKeys(false)){int cmd=old.getInt(slot+".custom-model-data",-1);if(cmd>=0)yaml.set("visual.slots."+slot+".custom-model-data",cmd);}}
        yaml.set("meta.schema",1);yaml.set("meta.id",id);yaml.set("meta.source","GoldenPotScan 0.0.1");
        yaml.set("recognition.title",title);yaml.set("recognition.size",inv.getSize());yaml.set("visual.enabled",file.exists()&&YamlConfiguration.loadConfiguration(file).getBoolean("visual.enabled",false));
        for(int i=0;i<inv.getSize();i++){
            ItemStack item=inv.getItem(i);String base="snapshot.slots."+i;
            yaml.set(base+".material",item==null||item.getType().isAir()?"AIR":item.getType().name());
            if(item!=null&&!item.getType().isAir()){
                yaml.set(base+".amount",item.getAmount());ItemMeta meta=item.getItemMeta();if(meta!=null){
                    if(meta.hasDisplayName())yaml.set(base+".display-name",meta.getDisplayName());
                    if(meta.hasCustomModelData())yaml.set(base+".legacy-custom-model-data",meta.getCustomModelData());
                    if(meta.hasLore())yaml.set(base+".lore",meta.getLore());
                }
            }
        }
        try{yaml.save(file);menus.put(id,yaml);player.sendMessage("§a[GoldenPotScan] Saved: menus/"+id+".yml ("+inv.getSize()+" slots)");log("Saved menu "+id);}catch(IOException ex){getLogger().severe("Menu save failed: "+ex.getMessage());player.sendMessage("§c[GoldenPotScan] YAML save FAILED. Check server console.");}
    }
    @EventHandler(priority=EventPriority.MONITOR,ignoreCancelled=true) public void onOpen(InventoryOpenEvent event){
        if(!(event.getPlayer() instanceof Player player))return;
        String request=pending.remove(player.getUniqueId());
        if(request!=null){long delay=Math.max(1,getConfig().getLong("menu-manager.capture-delay-ticks",2));Bukkit.getScheduler().runTaskLater(this,()->{if(player.isOnline())capture(player,request);},delay);return;}
        if(!getConfig().getBoolean("menu-manager.enabled",true)||!visual)return;
        Bukkit.getScheduler().runTaskLater(this,()->{if(player.isOnline())applyVisual(player);},2);
    }
    @EventHandler(priority=EventPriority.MONITOR) public void onClick(InventoryClickEvent e){if(visual&&e.getWhoClicked() instanceof Player p)Bukkit.getScheduler().runTaskLater(this,()->{if(p.isOnline())applyVisual(p);},2);}
    @EventHandler(priority=EventPriority.MONITOR) public void onDrag(InventoryDragEvent e){if(visual&&e.getWhoClicked() instanceof Player p)Bukkit.getScheduler().runTaskLater(this,()->{if(p.isOnline())applyVisual(p);},2);}
    private void applyVisual(Player p){
        if(!visual)return;InventoryView view=p.getOpenInventory();String id=idFor(view);if(id==null)return;
        YamlConfiguration yaml=menus.get(id);if(!yaml.getBoolean("visual.enabled",false))return;
        ConfigurationSection slots=yaml.getConfigurationSection("visual.slots");if(slots==null)return;
        Inventory inv=view.getTopInventory();for(String s:slots.getKeys(false)){
            int index;try{index=Integer.parseInt(s);}catch(NumberFormatException x){continue;}
            if(index<0||index>=inv.getSize())continue;
            ItemStack original=inv.getItem(index);if(original==null||original.getType()!=Material.GRAY_STAINED_GLASS_PANE)continue;
            int cmd=slots.getInt(s+".custom-model-data",-1);if(cmd<0)continue;
            ItemMeta meta=original.getItemMeta();if(meta==null)continue;
            if(meta.hasCustomModelData()&&meta.getCustomModelData()==cmd)continue;
            ItemStack cloned=original.clone();ItemMeta cloneMeta=cloned.getItemMeta();if(cloneMeta==null)continue;
            cloneMeta.setCustomModelData(cmd);cloned.setItemMeta(cloneMeta);inv.setItem(index,cloned);
        }
    }
    private void initBookRules(){
        String data="projectile_protection:2426,bane_of_arthropods:2401,blast_protection:2403,feather_falling:2409,fire_protection:2411,luck_of_the_sea:2420,vanishing_curse:2441,aqua_affinity:2400,binding_curse:2405,depth_strider:2407,sweeping_edge:2436,frost_walker:2414,quick_charge:2429,fire_aspect:2410,respiration:2430,swift_sneak:2437,channeling:2404,efficiency:2408,protection:2427,silk_touch:2434,soul_speed:2435,unbreaking:2439,wind_burst:2440,knockback:2417,multishot:2423,sharpness:2432,impaling:2415,infinity:2416,piercing:2424,density:2406,fortune:2413,looting:2418,loyalty:2419,mending:2422,riptide:2431,breach:2402,thorns:2438,flame:2412,power:2425,punch:2428,smite:2433,lunge:2442,lure:2421";
        for(String entry:data.split(",")){String[] pair=entry.split(":");bookCmd.put(pair[0],Integer.parseInt(pair[1]));}
    }
    private String detectGem(ItemStack item){
        if(item==null||!item.hasItemMeta())return null;
        String id=item.getItemMeta().getPersistentDataContainer().get(new NamespacedKey("theosis","gem_id"),PersistentDataType.STRING);
        if(id==null)return null;String key=id.toLowerCase(Locale.ROOT);return Set.of("ruby","sapphire","topaz","emerald").contains(key)?key:null;
    }
    private void loadTemplates(){YamlConfiguration yaml=YamlConfiguration.loadConfiguration(templatesFile);for(String key:List.of("ruby","sapphire","topaz","emerald")){ItemStack item=yaml.getItemStack(key);if(item!=null)gemTemplates.put(key,item);}}
    private void template(Player p,String key){
        if(!Set.of("ruby","sapphire","topaz","emerald").contains(key)){p.sendMessage("§cUse ruby|sapphire|topaz|emerald");return;}
        ItemStack hand=p.getInventory().getItemInMainHand();if(hand.getType().isAir()){p.sendMessage("§cHold a NEW Theosis Tier 1 gem.");return;}
        ItemStack item=hand.clone();item.setAmount(1);gemTemplates.put(key,item);
        YamlConfiguration yaml=YamlConfiguration.loadConfiguration(templatesFile);yaml.set(key,item);
        try{yaml.save(templatesFile);p.sendMessage("§aGoldenPotScan: gem template saved: "+key);}catch(IOException ex){p.sendMessage("§cCould not save template.");getLogger().severe(ex.getMessage());}
    }
    private int bookModel(ItemStack item){
        if(item.getType()!=Material.ENCHANTED_BOOK||!(item.getItemMeta() instanceof EnchantmentStorageMeta meta))return -1;
        for(var rule:bookCmd.entrySet())for(Enchantment enchant:meta.getStoredEnchants().keySet())if(enchant.getKey().getKey().equals(rule.getKey()))return rule.getValue();
        return -1;
    }
    private static String normalizeName(String text){return Normalizer.normalize(text.toLowerCase(Locale.ROOT),Normalizer.Form.NFC);}
    private int brewModel(ItemStack item){
        if(!item.hasItemMeta())return -1;ItemMeta meta=item.getItemMeta();
        if(!meta.getPersistentDataContainer().has(new NamespacedKey("breweryx","brewdata")))return -1;
        if(meta.hasCustomModelData())return -1;
        String n=normalizeName(plain(meta.hasDisplayName()?meta.getDisplayName():""));
        if(n.contains("cerveja de trigo"))return 2500;if(n.contains("cerveja escura"))return 2502;if(n.contains("cerveja"))return 2501;
        if(n.contains("vinho"))return 2503;if(n.contains("hidromel")&&n.contains("maçã"))return 2505;if(n.contains("hidromel"))return 2504;
        if(n.contains("sidra"))return 2506;if(n.contains("licor de maçã"))return 2507;
        if(n.contains("vodka")&&n.contains("dourad"))return 2519;if(n.contains("vodka")&&(n.contains("cogumelo")||n.contains("brilhante")))return 2511;if(n.contains("vodka"))return 2510;
        if(n.contains("whiskey")&&(n.contains("fogo")||n.contains("real")))return 2520;if(n.contains("whiskey"))return 2508;
        if(n.contains("rum"))return 2509;if(n.contains("gin"))return 2512;if(n.contains("tequila")||n.contains("mezcal"))return 2513;
        if(n.contains("absinto")&&(n.contains("verde")||n.contains("brilhante")))return 2515;if(n.contains("absinto")||n.contains("absinthe"))return 2514;
        if(n.contains("sopa de batata"))return 2516;if(n.contains("café gelado"))return 2522;if(n.contains("café"))return 2517;
        if(n.contains("gemada"))return 2518;if(n.contains("chocolate quente"))return 2521;return 2508;
    }
    private ItemStack convert(ItemStack source){
        if(source==null||source.getType().isAir())return null;
        if(getConfig().getBoolean("item-manager.theosis-legacy-gems",true)){
            String gem=detectGem(source);if(gem!=null&&gemTemplates.containsKey(gem)){
                ItemStack replacement=gemTemplates.get(gem).clone();replacement.setAmount(source.getAmount());
                if(!source.isSimilar(replacement))return replacement;
            }
        }
        int cmd=-1;
        if(getConfig().getBoolean("item-manager.enchanted-books",true))cmd=bookModel(source);
        if(cmd<0&&getConfig().getBoolean("item-manager.breweryx",true))cmd=brewModel(source);
        if(cmd<0)return null;
        ItemMeta meta=source.getItemMeta();if(meta==null)return null;
        if(meta.hasCustomModelData()&&meta.getCustomModelData()==cmd)return null;
        ItemStack changed=source.clone();ItemMeta changedMeta=changed.getItemMeta();if(changedMeta==null)return null;
        changedMeta.setCustomModelData(cmd);changed.setItemMeta(changedMeta);return changed;
    }
    private void scanAll(){if(!itemEnabled)return;for(Player p:Bukkit.getOnlinePlayers()){
        scanInventory(p.getInventory());Inventory top=p.getOpenInventory().getTopInventory();if(top!=p.getInventory()&&top.getType()!=InventoryType.ANVIL&&top.getType()!=InventoryType.CRAFTING&&top.getType()!=InventoryType.PLAYER)scanInventory(top);
    }}
    private void scanInventory(Inventory inv){for(int i=0;i<inv.getSize();i++){ItemStack original=inv.getItem(i);ItemStack changed=convert(original);if(changed!=null)inv.setItem(i,changed);}}
    @EventHandler(priority=EventPriority.MONITOR,ignoreCancelled=true) public void goldenAnvil(InventoryClickEvent e){
        if(!getConfig().getBoolean("item-manager.golden-anvil",false)||e.getView().getTopInventory().getType()!=InventoryType.ANVIL)return;
        if(e.getRawSlot()!=1)return;
        if(!(e.getWhoClicked() instanceof Player p))return;
        Bukkit.getScheduler().runTaskLater(this,()->{
            Inventory top=p.getOpenInventory().getTopInventory();if(top.getType()!=InventoryType.ANVIL)return;
            ItemStack item=top.getItem(1);if(item==null||item.getType()!=Material.ENCHANTED_BOOK||!item.hasItemMeta())return;
            ItemMeta meta=item.getItemMeta();if(!meta.hasCustomModelData())return;
            int cmd=meta.getCustomModelData();if(cmd<2400||cmd>2499)return;
            ItemStack clone=item.clone();ItemMeta cm=clone.getItemMeta();cm.setCustomModelData(null);clone.setItemMeta(cm);top.setItem(1,clone);
        },1);
    }
    @Override public boolean onCommand(CommandSender sender,Command command,String label,String[] args){
        if(args.length==0||args[0].equalsIgnoreCase("help")){sender.sendMessage("§6GoldenPotScan §f/gps menus scan auto|<id>|cancel; /gps menus list|reload|mode on|off|log on|off; /gps items status|mode on|off|template <gem>; /gps reload");return true;}
        if(args[0].equalsIgnoreCase("reload")){reloadConfig();loadMenus();loadTemplates();visual=getConfig().getBoolean("menu-manager.visual-enabled",false);itemEnabled=getConfig().getBoolean("item-manager.enabled",false);logging=getConfig().getBoolean("menu-manager.log",false);sender.sendMessage("§aGoldenPotScan reloaded.");return true;}
        if(args[0].equalsIgnoreCase("menus")){
            if(args.length>=2&&args[1].equalsIgnoreCase("list")){sender.sendMessage("§eMenus: "+String.join(", ",menus.keySet()));return true;}
            if(args.length>=2&&args[1].equalsIgnoreCase("reload")){loadMenus();sender.sendMessage("§aYAML menu cache reloaded: "+menus.size());return true;}
            if(args.length>=3&&args[1].equalsIgnoreCase("mode")){visual=args[2].equalsIgnoreCase("on");getConfig().set("menu-manager.visual-enabled",visual);saveConfig();sender.sendMessage("§eVisual mode: "+visual);return true;}
            if(args.length>=3&&args[1].equalsIgnoreCase("log")){logging=args[2].equalsIgnoreCase("on");getConfig().set("menu-manager.log",logging);saveConfig();sender.sendMessage("§eMenu logging: "+logging);return true;}
            if(args.length>=3&&args[1].equalsIgnoreCase("scan")){
                if(!(sender instanceof Player p)){sender.sendMessage("§cUse scan in-game.");return true;}
                if(args[2].equalsIgnoreCase("cancel")){pending.remove(p.getUniqueId());p.sendMessage("§ePending capture cancelled.");return true;}
                pending.put(p.getUniqueId(),args[2]);p.sendMessage("§aOpen the next plugin menu to capture: "+args[2]);return true;
            }
        }
        if(args[0].equalsIgnoreCase("items")){
            if(args.length>=2&&args[1].equalsIgnoreCase("status")){sender.sendMessage("§eItem scanner: "+itemEnabled+"; templates="+gemTemplates.keySet());return true;}
            if(args.length>=3&&args[1].equalsIgnoreCase("mode")){itemEnabled=args[2].equalsIgnoreCase("on");getConfig().set("item-manager.enabled",itemEnabled);saveConfig();sender.sendMessage("§eItem scanner: "+itemEnabled);return true;}
            if(args.length>=3&&args[1].equalsIgnoreCase("template")&&sender instanceof Player p){template(p,args[2].toLowerCase(Locale.ROOT));return true;}
        }
        sender.sendMessage("§cUnknown argument. /gps help");return true;
    }
    @Override public List<String> onTabComplete(CommandSender sender,Command cmd,String alias,String[] args){
        if(args.length==1)return Arrays.asList("help","menus","items","reload");
        if(args.length==2&&args[0].equalsIgnoreCase("menus"))return Arrays.asList("scan","list","reload","mode","log");
        if(args.length==2&&args[0].equalsIgnoreCase("items"))return Arrays.asList("status","mode","template");
        if(args.length==3&&args[1].equalsIgnoreCase("scan"))return Arrays.asList("auto","cancel");
        if(args.length==3&&args[1].equalsIgnoreCase("template"))return Arrays.asList("ruby","sapphire","emerald","topaz");
        if(args.length==3&&Arrays.asList("mode","log").contains(args[1].toLowerCase(Locale.ROOT)))return Arrays.asList("on","off");return Collections.emptyList();
    }
}
