package br.com.ethercraft.goldenpot;
import org.bukkit.*;
import org.bukkit.block.*;
import org.bukkit.command.*;
import org.bukkit.entity.Player;
import org.bukkit.event.*;
import org.bukkit.event.block.*;
import org.bukkit.event.entity.EntityExplodeEvent;
import org.bukkit.event.player.*;
import org.bukkit.inventory.*;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.java.JavaPlugin;
import java.util.*;
import java.nio.file.*;
import java.security.MessageDigest;

public final class GoldenPotGen extends JavaPlugin implements Listener {
 private NamespacedKey identity;
 private BedrockBridge bridge;
 private boolean ready, enabled;
 private String failure="";
 @Override public void onLoad(){
  try{
   saveDefaultConfig();enabled=getConfig().getBoolean("experimental-blocks",true);
   for(String name:List.of("CraftEngine","Oraxen","Nexo"))if(getServer().getPluginManager().getPlugin(name)!=null)enabled=false;
   Resources.prepare(getDataFolder().toPath(),this::getResource,enabled);ready=true;
   if(getServer().getPluginManager().getPlugin("Geyser-Spigot")!=null){bridge=new BedrockBridge(this);bridge.attach();}
  }catch(Exception|LinkageError ex){failure=ex.toString();getLogger().severe("Initialization failed: "+failure);ready=false;}
 }
 @Override public void onEnable(){
  identity=new NamespacedKey(this,"content_id");
  enabled=ready&&enabled;
  for(String name:List.of("CraftEngine","Oraxen","Nexo"))if(getServer().getPluginManager().getPlugin(name)!=null){enabled=false;getLogger().warning("Custom block placement disabled: carrier conflict requires review with "+name);}
  getServer().getPluginManager().registerEvents(this,this);
  getLogger().info("GoldenPotGen 0.2.0-preview. One plugin, two resource packs. Experimental blocks: "+enabled);
 }
 @Override public void onDisable(){if(bridge!=null)bridge.close();}
 private NamespacedKey position(Block b){return new NamespacedKey(this,"b_"+(b.getX()&15)+"_"+(b.getY()-b.getWorld().getMinHeight())+"_"+(b.getZ()&15));}
 private boolean marked(Block b){return Resources.ID.equals(b.getChunk().getPersistentDataContainer().get(position(b),PersistentDataType.STRING));}
 boolean experimental(){return enabled;}
 private boolean custom(Block b){return b.getType()==Material.NOTE_BLOCK&&marked(b);}
 private boolean custom(ItemStack i){return i!=null&&i.hasItemMeta()&&Resources.ID.equals(i.getItemMeta().getPersistentDataContainer().get(identity,PersistentDataType.STRING));}
 private ItemStack item(){
  ItemStack i=new ItemStack(Material.NOTE_BLOCK);var m=i.getItemMeta();
  m.setDisplayName("§bMinério de Ambrósio");m.setItemModel(NamespacedKey.fromString(Resources.ID));m.setCustomModelData(720001);
  m.getPersistentDataContainer().set(identity,PersistentDataType.STRING,Resources.ID);i.setItemMeta(m);return i;
 }
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void placing(BlockPlaceEvent e){
  if(!custom(e.getItemInHand()))return;
  if(!enabled){e.setCancelled(true);e.getPlayer().sendMessage("§eGoldenPotGen: blocos experimentais desativados. Consulte /gpg status.");return;}
  e.getBlockPlaced().setBlockData(Bukkit.createBlockData(Resources.STATE),false);
 }
 @EventHandler(priority=EventPriority.MONITOR,ignoreCancelled=true) public void placed(BlockPlaceEvent e){
  if(enabled&&custom(e.getItemInHand())&&e.getBlockPlaced().getBlockData().getAsString().equals(Resources.STATE))
   e.getBlockPlaced().getChunk().getPersistentDataContainer().set(position(e.getBlockPlaced()),PersistentDataType.STRING,Resources.ID);
 }
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void breaking(BlockBreakEvent e){if(custom(e.getBlock())){e.setDropItems(false);e.setExpToDrop(0);}}
 @EventHandler(priority=EventPriority.MONITOR,ignoreCancelled=true) public void broken(BlockBreakEvent e){
  if(!custom(e.getBlock()))return;
  e.getBlock().getChunk().getPersistentDataContainer().remove(position(e.getBlock()));
  if(e.getPlayer().getGameMode()!=GameMode.CREATIVE)e.getBlock().getWorld().dropItemNaturally(e.getBlock().getLocation().add(.5,.5,.5),item());
 }
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void physics(BlockPhysicsEvent e){if(custom(e.getBlock()))e.setCancelled(true);}
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void sound(NotePlayEvent e){if(custom(e.getBlock()))e.setCancelled(true);}
 @EventHandler(priority=EventPriority.HIGHEST) public void interact(PlayerInteractEvent e){
  if(e.getClickedBlock()!=null&&custom(e.getClickedBlock())){
   // Suppress note tuning while allowing normal adjacent block placement.
   e.setUseInteractedBlock(Event.Result.DENY);
  }
 }
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void extend(BlockPistonExtendEvent e){if(e.getBlocks().stream().anyMatch(this::custom))e.setCancelled(true);}
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void retract(BlockPistonRetractEvent e){if(e.getBlocks().stream().anyMatch(this::custom))e.setCancelled(true);}
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void blast(EntityExplodeEvent e){e.blockList().removeIf(this::custom);}
 @EventHandler(priority=EventPriority.HIGHEST,ignoreCancelled=true) public void blast(BlockExplodeEvent e){e.blockList().removeIf(this::custom);}
 @EventHandler public void join(PlayerJoinEvent e){if(getConfig().getBoolean("java-pack.send-on-join",false))sendPack(e.getPlayer());}
 private void sendPack(Player p){
  String url=getConfig().getString("java-pack.url","");
  if(!url.startsWith("https://")&&!url.startsWith("http://")){p.sendMessage("§eConfigure java-pack.url com o ZIP Java gerado e hospedado.");return;}
  try{
   byte[] bytes=Files.readAllBytes(getDataFolder().toPath().resolve("generated/EtherTexture-Java-GoldenPotGen.zip"));
   p.setResourcePack(url,MessageDigest.getInstance("SHA-1").digest(bytes));
  }catch(Exception ex){p.sendMessage("§cFalha ao enviar o pack: "+ex.getMessage());}
 }
 @Override public boolean onCommand(CommandSender sender,Command command,String label,String[] args){
  if(!sender.hasPermission("goldenpotgen.admin")){sender.sendMessage("§cSem permissão.");return true;}
  String sub=args.length==0?"status":args[0].toLowerCase(Locale.ROOT);
  switch(sub){
   case "status" -> {
    sender.sendMessage("§6GoldenPotGen 0.2.0-preview");sender.sendMessage("§7Packs: "+(ready?"gerados":"falha: "+failure));
    sender.sendMessage("§7Bloco experimental: "+enabled+" | ID: "+Resources.ID);
    sender.sendMessage("§7Geyser: "+(bridge==null?"ausente":"blocos="+bridge.blocks+", itens="+bridge.items+", pack="+bridge.pack));
    sender.sendMessage("§7A migração de outros plugins e móveis ainda não está implementada.");
   }
   case "give" -> {
    if(!(sender instanceof Player p)){sender.sendMessage("Execute no jogo.");break;}
    if(!enabled){sender.sendMessage("§eAtive experimental-blocks em um servidor de teste e reinicie.");break;}
    for(ItemStack left:p.getInventory().addItem(item()).values())p.getWorld().dropItemNaturally(p.getLocation(),left);
   }
   case "pack" -> {if(sender instanceof Player p)sendPack(p);else sender.sendMessage("Packs em plugins/GoldenPotGen/generated/");}
   default -> sender.sendMessage("§e/gpg status | /gpg give | /gpg pack");
  }return true;
 }
}
