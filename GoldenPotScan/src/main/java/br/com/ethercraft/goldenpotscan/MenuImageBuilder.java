package br.com.ethercraft.goldenpotscan;

import org.bukkit.Material;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.java.JavaPlugin;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;

final class MenuImageBuilder {
    private MenuImageBuilder() {}
    static void build(JavaPlugin plugin, CommandSender sender, File menuFile, String name, int firstSlot, int rows, int firstCmd) {
        if (!name.matches("[a-zA-Z0-9_-]{1,48}") || rows < 1 || rows > 6 || firstCmd < 2300) {
            sender.sendMessage("§cInvalid name, rows (1..6), or CMD (minimum 2300)."); return;
        }
        File imageFile = new File(plugin.getDataFolder(), "images/" + name + ".png");
        if (!imageFile.isFile()) { sender.sendMessage("§cPlace image at plugins/GoldenPotScan/images/" + name + ".png"); return; }
        try {
            BufferedImage input = ImageIO.read(imageFile);
            if (input == null || input.getWidth() % 9 != 0 || input.getHeight() % rows != 0) {
                sender.sendMessage("§cPNG dimensions must divide evenly into 9 columns and " + rows + " rows."); return;
            }
            int tileW = input.getWidth()/9, tileH = input.getHeight()/rows;
            if (tileW != tileH) { sender.sendMessage("§cEach fragment must be square. Expected height: " + (tileW*rows)); return; }
            YamlConfiguration menu = YamlConfiguration.loadConfiguration(menuFile);
            int size = menu.getInt("recognition.size");
            if (size <= 0 || size % 9 != 0 || firstSlot < 0 || firstSlot % 9 != 0 || firstSlot + rows*9 > size) {
                sender.sendMessage("§cStart slot must begin a row (0, 9, 18...) and fit inside the menu."); return;
            }
            Map<String,List<Integer>> materials = new LinkedHashMap<>();
            for (int i=0;i<rows*9;i++) {
                int slot=firstSlot+i;
                String material=menu.getString("snapshot.slots."+slot+".material","AIR");
                Material mat=Material.matchMaterial(material);
                if (mat==null || mat.isAir() || !mat.isItem()) {
                    sender.sendMessage("§cSlot "+slot+" is "+material+". Fill all image slots with items and scan menu again. No changes saved.");return;
                }
                materials.computeIfAbsent(material.toLowerCase(Locale.ROOT),k->new ArrayList<>()).add(i);
            }
            File outputDir=new File(plugin.getDataFolder(),"generated");
            if (!outputDir.exists()&&!outputDir.mkdirs()) throw new IOException("Cannot create generated folder");
            File zipFile=new File(outputDir,name+"-fragments.zip");
            try (ZipOutputStream zip=new ZipOutputStream(new FileOutputStream(zipFile))) {
                for (int i=0;i<rows*9;i++) {
                    int x=(i%9)*tileW, y=(i/9)*tileH;
                    BufferedImage tile=input.getSubimage(x,y,tileW,tileH);
                    ByteArrayOutputStream png=new ByteArrayOutputStream();
                    ImageIO.write(tile,"png",png);
                    add(zip,"assets/goldenpotscan/textures/item/"+name+"_"+i+".png",png.toByteArray());
                    String model="{\"parent\":\"minecraft:item/generated\",\"textures\":{\"layer0\":\"goldenpotscan:item/"+name+"_"+i+"\"}}";
                    add(zip,"assets/goldenpotscan/models/item/"+name+"_"+i+".json",model.getBytes(StandardCharsets.UTF_8));
                }
                for (var entry:materials.entrySet()) {
                    String material=entry.getKey();
                    StringBuilder json=new StringBuilder("{\"model\":{\"type\":\"minecraft:range_dispatch\",\"property\":\"minecraft:custom_model_data\",\"index\":0,\"fallback\":{\"type\":\"minecraft:model\",\"model\":\"minecraft:item/"+material+"\"},\"entries\":[");
                    List<Integer> indices=entry.getValue();
                    for (int j=0;j<indices.size();j++) {
                        int i=indices.get(j);
                        if (j>0)json.append(',');
                        json.append("{\"threshold\":").append(firstCmd+i).append(",\"model\":{\"type\":\"minecraft:model\",\"model\":\"goldenpotscan:item/").append(name).append('_').append(i).append("\"}}");
                    }
                    // Ensure CMD values outside this image's range fall back to the vanilla item.
                    json.append(",{\"threshold\":").append(firstCmd+rows*9).append(",\"model\":{\"type\":\"minecraft:model\",\"model\":\"minecraft:item/").append(material).append("\"}}]}}");
                    add(zip,"assets/minecraft/items/"+material+".json",json.toString().getBytes(StandardCharsets.UTF_8));
                }
                String readme="GoldenPotScan image fragments: "+name+"\nMerge assets into your Java resource pack.\nIMPORTANT: assets/minecraft/items/*.json are generated templates; merge their CMD entries with existing definitions instead of replacing existing mappings.\nImage layout: 9 columns x "+rows+" rows, "+tileW+" pixels per tile.\nMenu: "+menuFile.getName()+"; first slot "+firstSlot+"; first CMD "+firstCmd+".\n";
                add(zip,"README-GoldenPotScan.txt",readme.getBytes(StandardCharsets.UTF_8));
            }
            for (int i=0;i<rows*9;i++) {
                String key="visual.slots."+(firstSlot+i);
                menu.set(key+".custom-model-data",firstCmd+i);
                menu.set(key+".mode","OVERRIDE");
            }
            menu.set("visual.enabled",true);
            menu.save(menuFile);
            sender.sendMessage("§aGenerated "+(rows*9)+" fragments and saved menu CMDs.");
            sender.sendMessage("§eResource pack assets: plugins/GoldenPotScan/generated/"+zipFile.getName());
            sender.sendMessage("§eMerge JSON definitions with existing pack mappings; do not blindly overwrite.");
        } catch(Exception ex) {
            plugin.getLogger().warning("Image generation failed: "+ex);
            sender.sendMessage("§cImage generation failed: "+ex.getMessage());
        }
    }
    private static void add(ZipOutputStream zip,String path,byte[] data)throws IOException {
        zip.putNextEntry(new ZipEntry(path));zip.write(data);zip.closeEntry();
    }
}
